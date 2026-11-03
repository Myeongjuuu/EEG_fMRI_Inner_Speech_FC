"""Compatibility entry point for the ds006033.eeg module."""
from .ds006033.eeg import BANDS, METHODS, WORDS, analyze_eeg, main, paired_events


if __name__ == "__main__":
    main()
