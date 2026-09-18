from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from core.author_mapper import UNMAPPED, apply_row_resolutions, load_row_resolutions, save_row_resolutions
from core.metrics import filter_records
from core.review_state import apply_duplicate_decisions, load_duplicate_decisions, save_duplicate_decisions


def test_manual_unmapped_resolution_is_explicit_and_persisted():
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "unmapped.json"
        save_row_resolutions({"PUB1": "Patil Mounica"}, path)
        saved = load_row_resolutions(path)
        frame = pd.DataFrame(
            {"Publication ID": ["PUB1", "PUB2"], "Faculty Name": [UNMAPPED, UNMAPPED], "Mapping Status": ["Unmapped", "Unmapped"]}
        )
        result = apply_row_resolutions(frame, saved)
        assert result.loc[0, "Faculty Name"] == "Patil Mounica"
        assert result.loc[0, "Mapping Status"] == "Manually resolved"
        assert result.loc[1, "Faculty Name"] == UNMAPPED


def test_duplicate_exclusion_requires_saved_user_decision():
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "duplicates.json"
        save_duplicate_decisions({"PUB1": "Exclude", "PUB2": "Include"}, path)
        frame = pd.DataFrame(
            {
                "Publication ID": ["PUB1", "PUB2", "PUB3"],
                "Possible Duplicate": ["Yes", "Yes", "No"],
                "Calendar Year": [2024, 2024, 2024],
                "Faculty Name": ["A", "A", "A"],
                "Publication Type": ["Journal", "Journal", "Journal"],
                "Quartile": ["Q1", "Q1", "Q1"],
                "SCI_SCIE_Flag": [1, 1, 1],
                "ESCI_Flag": [0, 0, 0],
                "Scopus_Flag": [1, 1, 1],
            }
        )
        reviewed = apply_duplicate_decisions(frame, load_duplicate_decisions(path))
        assert len(filter_records(reviewed, include_duplicates=True)) == 3
        assert list(filter_records(reviewed, include_duplicates=False)["Publication ID"]) == ["PUB2", "PUB3"]
