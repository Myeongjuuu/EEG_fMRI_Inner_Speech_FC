"""Nilearn task-regressed ROI connectivity from ds006033 fMRIPrep derivatives."""
import argparse
import json
from pathlib import Path

import nibabel as nib
from nilearn.datasets import fetch_atlas_schaefer_2018
from nilearn.glm.first_level import make_first_level_design_matrix
from nilearn.maskers import NiftiLabelsMasker
from nilearn.signal import clean
import numpy as np
import pandas as pd

SPACE = "MNI152NLin6Asym"
MOTION = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]


def analyze_bold(bold, mask, confounds, events, tr, atlas, output):
    image = nib.load(bold)
    if len(image.shape) != 4:
        raise ValueError('Expected a four-dimensional preprocessed BOLD image')
    n_scans = image.shape[-1]
    nuisance = pd.read_csv(confounds, sep="\t")
    if len(nuisance) != n_scans or not np.isfinite(tr) or tr <= 0:
        raise ValueError("BOLD volumes, confounds or TR are inconsistent")
    fd = nuisance.framewise_displacement.copy()
    if pd.isna(fd.iloc[0]):
        fd.iloc[0] = 0
    motion = nuisance[MOTION + ["white_matter", "csf"]]
    if not np.isfinite(motion).all().all() or not np.isfinite(fd).all():
        raise ValueError("Missing or nonfinite motion/tissue confounds")
    censor = (fd > .5).to_numpy()
    outliers = nuisance.filter(regex=r"^(non_steady_state_outlier|motion_outlier)")
    censor |= outliers.fillna(0).ne(0).any(axis=1).to_numpy()
    keep = np.flatnonzero(~censor)
    if len(keep) < 60:
        raise ValueError(f"Only {len(keep)} usable BOLD volumes after censoring")
    timing = pd.read_csv(events, sep="\t")[["onset", "duration", "trial_type"]]
    timing = timing[timing.trial_type != "rest"]
    # Match the midpoint slice-time reference used in the documented fMRIPrep run.
    design = make_first_level_design_matrix((np.arange(n_scans) + .5) * tr, events=timing,
                                            hrf_model="spm + derivative", drift_model="cosine",
                                            high_pass=.01)
    regressors = np.column_stack([motion, design])
    masker = NiftiLabelsMasker(labels_img=atlas, mask_img=mask, resampling_target="data",
                              strategy="mean", standardize=None, keep_masked_labels=False)
    signals = masker.fit_transform(image)
    if len(keep) - np.linalg.matrix_rank(regressors[keep]) < 30:
        raise ValueError("Insufficient residual degrees of freedom")
    residual = clean(signals, confounds=regressors, sample_mask=keep,
                     detrend=False, standardize=None, filter=False)
    if not np.isfinite(residual).all() or (residual.std(axis=0) <= 1e-8).any():
        raise ValueError("Nonfinite or constant residual ROI time series")
    labels = masker.region_ids_
    ids = [labels[i] for i in range(residual.shape[1])]
    matrix = pd.DataFrame(np.corrcoef(residual, rowvar=False), index=ids, columns=ids)
    output.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(output / "background_connectivity.csv", index_label="schaefer_roi")
    design.to_csv(output / "task_design.csv", index_label="time_s")
    pd.DataFrame(dict(frame=np.arange(n_scans), fd_mm=fd, retained=~censor)).to_csv(
        output / "frame_qc.csv", index=False)
    summary = dict(n_scans=n_scans, retained=len(keep), n_rois=len(ids), tr=tr,
                   space=SPACE, slice_time_ref=.5, bold=str(bold), events=str(events), atlas=str(atlas))
    (output / "qc.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("derivatives", type=Path, help="Root of the fMRIPrep derivatives")
    parser.add_argument("output", type=Path)
    parser.add_argument("--subject", default="sub-02")
    parser.add_argument("--session", default="ses-01")
    args = parser.parse_args()
    prefix = f"{args.subject}_{args.session}_task-innerspeech"
    source = args.dataset / args.subject / args.session / "func"
    folder = args.derivatives / args.subject / args.session / "func"
    bold = folder / f"{prefix}_space-{SPACE}_res-2_desc-preproc_bold.nii.gz"
    mask = folder / f"{prefix}_space-{SPACE}_res-2_desc-brain_mask.nii.gz"
    confounds = folder / f"{prefix}_desc-confounds_timeseries.tsv"
    for path in (bold, mask, confounds):
        if not path.is_file():
            parser.error(f"Missing fMRIPrep derivative: {path}")
    # Use the atlas distributed in MNI152NLin6Asym and require matching fMRIPrep space.
    tr = json.loads((source / f"{prefix}_bold.json").read_text())["RepetitionTime"]
    atlas = fetch_atlas_schaefer_2018(n_rois=100, yeo_networks=7, resolution_mm=2, data_dir=args.output / "atlas").maps
    analyze_bold(bold, mask, confounds, source / f"{prefix}_events.tsv", tr, atlas,
                 args.output / args.subject / args.session)


if __name__ == "__main__":
    main()
