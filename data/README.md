# Dataset layout

## ds003626 v2.1.2 · EEG

Download OpenNeuro **ds003626**, version **2.1.2**, separately. Do not commit recordings or derivatives.

```
ds003626/
  sub-01/ses-01/eeg/sub-01_ses-01_task-innerspeech_eeg.bdf
  sub-01/ses-02/eeg/sub-01_ses-02_task-innerspeech_eeg.bdf
  ...
```

Copy `configs/default.yaml` to `configs/local.yaml` and set `dataset_root` and `output_root`. Relative paths resolve against the YAML's directory. The local configuration is ignored by Git. Derived FIF files are recreated from raw BDF, not taken from historical notebook outputs. Do not deserialize the dataset's `.dat`/`.pkl` derivatives: some are Python pickles despite their extension.

[Dataset DOI](https://doi.org/10.18112/openneuro.ds003626.v2.1.2), [data descriptor](https://doi.org/10.1038/s41597-022-01147-2), [authors' protocol implementation](https://github.com/N-Nieto/Inner_Speech_Dataset).

## ds006033 v1.0.0 · Simultaneous EEG and fMRI

Download the complete [OpenNeuro release](https://openneuro.org/datasets/ds006033/versions/1.0.0). The study includes three participants, with two planned sessions each. EEG is absent for `sub-01/ses-01` in the release. EEG uses BrainVision files with an EEG-specific events table. fMRI uses NIfTI BOLD images with a separate events table and T1w anatomical images.

```text
ds006033/
  sub-02/ses-01/eeg/sub-02_ses-01_task-innerspeech_eeg.vhdr
  sub-02/ses-01/eeg/sub-02_ses-01_task-innerspeech_eeg.vmrk
  sub-02/ses-01/eeg/sub-02_ses-01_task-innerspeech_eeg.eeg
  sub-02/ses-01/eeg/sub-02_ses-01_task-innerspeech_events.tsv
  sub-02/ses-01/func/sub-02_ses-01_task-innerspeech_bold.nii
  sub-02/ses-01/func/sub-02_ses-01_task-innerspeech_bold.json
  sub-02/ses-01/func/sub-02_ses-01_task-innerspeech_events.tsv
  sub-02/ses-01/anat/sub-02_ses-01_T1w.nii
  ...
```

Pass the dataset root to the ds006033 commands. The fMRI command also takes the fMRIPrep derivatives root. Keep downloaded recordings and derivatives outside Git. [Execution guide](../docs/ds006033.md) · [Data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC12681749/)
