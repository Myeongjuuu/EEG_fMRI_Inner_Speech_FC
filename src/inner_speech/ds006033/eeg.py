"""Session-held-out EEG analysis for the simultaneous OpenNeuro ds006033 study."""
import argparse
import json
import re
from pathlib import Path
import tempfile

import mne
import numpy as np
import pandas as pd

from ..classification import evaluate_csp
from ..connectivity import estimate_connectivity
from ..preprocessing import extract_pairs
from ..time_frequency import multitaper_power

WORDS = ("child", "daughter", "father", "four", "six", "ten", "three", "wife")
BANDS = dict(alpha=(8, 13))
METHODS = ["wpli2_debiased", "coh", "plv"]


def paired_events(path):
    events = pd.read_csv(path, sep="\t").sort_values("onset", kind="stable")
    if not np.isfinite(events[["onset", "duration"]]).all().all() or (events.duration <= 0).any():
        raise ValueError(f"Invalid event timing in {path}")
    unknown = set(events.trial_type) - {*WORDS, "rest", "fixation"}
    if unknown:
        raise ValueError(f"Unknown event types: {unknown}")
    rows = []
    for i in range(len(events) - 1):
        task, rest = events.iloc[i], events.iloc[i + 1]
        if task.trial_type not in WORDS or rest.trial_type != "rest":
            continue
        if task.duration < 1.5 or rest.duration < 3 or rest.onset < task.onset + task.duration - .002:
            continue
        rows.append(dict(trial_id=int(task.name), label=WORDS.index(task.trial_type) + 1,
                         word=task.trial_type, task_onset=task.onset + .5,
                         rest_onset=rest.onset + 2))
    return pd.DataFrame(rows, columns=["trial_id", "label", "word", "task_onset", "rest_onset"])


def analyze_eeg(header, events, output, scratch, peak_uv):
    pairs = paired_events(events)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        # Published headers retain the acquisition workstation's original filenames.
        staged = Path(folder) / header.name
        contents = header.read_text(encoding="utf-8-sig")
        for key, suffix in (("DataFile", ".eeg"), ("MarkerFile", ".vmrk")):
            companion = header.with_suffix(suffix).resolve(strict=True)
            contents, replacements = re.subn(
                rf"^{key}=.*$", lambda _: f"{key}={companion}", contents, count=1, flags=re.M)
            if replacements != 1:
                raise ValueError(f"Missing {key} in {header}")
        staged.write_text(contents, encoding="utf-8")
        raw = mne.io.read_raw_brainvision(staged, preload=str(Path(folder) / "eeg.dat"))
        if 'ECG' in raw.ch_names:
            raw.set_channel_types({'ECG': 'ecg'}, on_unit_change='ignore')
        raw.resample(256)
        raw.pick("eeg")
        raw.filter(1, 40)
        raw.set_eeg_reference("average")
        task, rest, rejected = extract_pairs(raw, pairs, 1, peak_uv, .1)
        raw.close()
        del raw
    rejected.to_csv(output / "rejected.csv", index=False)
    task.metadata.to_csv(output / "retained.csv", index=False)
    connectivity_path = output / "connectivity.npz"
    min_pairs = 20
    n_edges = 0
    if len(task) >= min_pairs:
        result = estimate_connectivity(task, rest, dict(
            bands=BANDS, methods=METHODS, min_trials=min_pairs, min_cycles=5, mt_bandwidth=4))
        np.savez_compressed(connectivity_path, **result)
        n_edges = len(result["edge_i"])
    else:
        connectivity_path.unlink(missing_ok=True)
        print(f"{output}: connectivity skipped ({len(task)} pairs, minimum {min_pairs})")
    for name, epochs in (("task", task), ("rest", rest)):
        power = multitaper_power(epochs)
        np.savez_compressed(output / f"{name}_power.npz", power=power.data,
                            freqs=power.freqs, times=power.times, channels=power.ch_names)
    summary = dict(candidate_pairs=len(pairs), retained_pairs=len(task),
                   word_counts=task.metadata.word.value_counts().to_dict(),
                   n_edges=n_edges, connectivity_min_pairs=min_pairs, reject_peak_to_peak_uv=peak_uv,
                   flat_peak_to_peak_uv=.1)
    (output / "qc.json").write_text(json.dumps(summary, indent=2))
    print(output, json.dumps(summary), flush=True)
    return task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--subject", default="sub-02")
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--reject-peak-to-peak-uv", type=float, default=200)
    args = parser.parse_args()
    if not np.isfinite(args.reject_peak_to_peak_uv) or args.reject_peak_to_peak_uv <= .1:
        parser.error("Peak-to-peak threshold must be finite and greater than 0.1 uV")
    epochs = []
    for session in ("ses-01", "ses-02"):
        prefix = f"{args.subject}_{session}_task-innerspeech"
        folder = args.dataset / args.subject / session / "eeg"
        header = folder / f"{prefix}_eeg.vhdr"
        if not header.is_file():
            print(f"{session}: EEG absent")
            continue
        ep = analyze_eeg(header, folder / f"{prefix}_events.tsv",
                         args.output / args.subject / session, args.scratch, args.reject_peak_to_peak_uv)
        epochs.append((session, ep))
    if len(epochs) < 2:
        print("Decoding requires two recorded EEG sessions.")
        return
    if epochs[0][1].ch_names != epochs[1][1].ch_names:
        raise ValueError("EEG channel order differs between sessions")
    X = np.concatenate([ep.get_data() for _, ep in epochs])
    y = np.concatenate([ep.events[:, 2] for _, ep in epochs])
    # Both sessions serve as training data. A singleton class gives LDA
    # a degenerate within-class covariance estimate.
    min_trials_per_word = 2
    for session, ep in epochs:
        counts = ep.metadata.word.value_counts().reindex(WORDS, fill_value=0)
        sparse = counts[counts < min_trials_per_word].to_dict()
        if sparse:
            print(f"{session}: decoding skipped; fewer than {min_trials_per_word} trials per word: {sparse}")
            return
    groups = [name for name, ep in epochs for _ in ep]
    for method in ("lda", "svm"):
        folds, predictions = evaluate_csp(X, y, groups, classifier=method)
        folds.to_csv(args.output / args.subject / f"csp_{method}_folds.csv", index=False)
        predictions.to_csv(args.output / args.subject / f"csp_{method}_predictions.csv", index=False)
        print(method, folds.to_string(index=False))


if __name__ == "__main__":
    main()
