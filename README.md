# Inner Speech EEG & fMRI Analysis

EEG preprocessing, run-held-out CSP classification, and exploratory task/rest connectivity analysis for the [Inner Speech dataset, ds003626 v2.1.2](https://doi.org/10.18112/openneuro.ds003626.v2.1.2).

Both dataset workflows run as Python modules from the terminal. The optional ds003626 notebooks call the shared Python analysis functions. See [validation status](docs/validation.md) and [analysis limits](docs/analysis_plan.md) for ds003626.

## Datasets

| OpenNeuro dataset | Recordings | Analysis in this repository |
| --- | --- | --- |
| [ds003626 v2.1.2](https://openneuro.org/datasets/ds003626/versions/2.1.2) | EEG from 10 participants performing inner speech, pronounced speech, and visualization tasks | EEG preprocessing, direction decoding, and exploratory EEG connectivity |
| [ds006033 v1.0.0](https://openneuro.org/datasets/ds006033/versions/1.0.0) | Simultaneous EEG and fMRI from three participants performing an eight-word inner-speech task | [Separate EEG and fMRI workflow](docs/ds006033.md) for EEG decoding, EEG connectivity and multitaper power, and BOLD ROI connectivity with fMRIPrep and Nilearn |

See the [dataset download and file layout guide](data/README.md).

## Layout

```text
configs/default.yaml              # Shared analysis settings
src/inner_speech/
  config.py                       # Paths and parameter validation
  events.py                       # Run/condition tracking and strict parsing
  preprocessing.py                # Filtering, resampling, ICA, paired QC
  classification.py               # CSP + LDA/SVM inside grouped CV
  connectivity.py                 # Matched task/rest wPLI-squared, coherence, PLV
  statistics.py                   # Participant differences, max-T, effect estimates
  time_frequency.py               # Multitaper TFR
  ds003626/cli.py                 # Staged EEG pipeline
  ds006033/eeg.py                 # Simultaneous-study EEG pipeline
  ds006033/fmri.py                # Simultaneous-study fMRI pipeline
notebooks/ds003626/               # Optional EEG analysis notebooks
notebooks/ds006033/               # Optional EEG and fMRI examples
tests/                            # Synthetic regression/scientific guards
docs/analysis_plan.md
docs/validation.md
data/README.md                    # Dataset preparation, no recordings
results/generated/                # Ignored local outputs and provenance
experiments/README.md             # Historical EEGNet attempt status
```

## Install and configure

Python 3.11 is the tested interpreter. From the repository root:

```bash
python -m venv .venv
# Activate the virtual environment for your shell.
python -m pip install -e .
```

Copy `configs/default.yaml` to `configs/local.yaml`. Set `dataset_root` to the separately downloaded dataset and `output_root` to a local results directory. Relative paths resolve against the YAML file. Set `preprocessing.scratch_dir` if the OS temporary drive has less than approximately 3 GiB free. Filtering/ICA also require substantial RAM and time. Review bad channels/ICA rather than assuming the starting settings suit every recording.

## Execute in stages

```bash
python -m inner_speech.ds003626.cli audit --config configs/local.yaml
# Review condition counts, event sequences and eligible pairs in the audit CSVs.
python -m inner_speech.ds003626.cli preprocess --config configs/local.yaml
python -m inner_speech.ds003626.cli connectivity --config configs/local.yaml
python -m inner_speech.ds003626.cli classify --config configs/local.yaml
# Only after all planned participants and sessions pass QC:
python -m inner_speech.ds003626.cli statistics --config configs/local.yaml
# Optional tests, after installing the dev extra
python -m pytest -q
```

For a first run, explicitly select `subjects: [sub-01]` and `sessions: [ses-01]` in the local config. This is an execution check, **not** a group analysis. Group inference requires at least five unique participants by default and fails if any planned session is missing. Use a different output directory for each changed configuration; generated files within a run directory are overwritten on rerun.

The five optional notebooks are in `notebooks/ds003626/`. They use `configs/default.yaml` unless environment variable `INNER_SPEECH_CONFIG` points to a local YAML. New notebooks contain no claimed results or saved executions.

## Sources

Primary sources: [data descriptor](https://doi.org/10.1038/s41597-022-01147-2), [authors' repository](https://github.com/N-Nieto/Inner_Speech_Dataset), [wPLI methods](https://doi.org/10.1016/j.neuroimage.2011.01.055), and [MNE-Connectivity](https://mne.tools/mne-connectivity/stable/generated/mne_connectivity.spectral_connectivity_epochs.html).
