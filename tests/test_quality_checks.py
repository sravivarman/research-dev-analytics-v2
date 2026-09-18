import pandas as pd

from core.author_mapper import UNMAPPED, apply_author_mappings
from core.quality_checks import quality_counts, unresolved_mapping_table, unmapped_records_table


def _quality_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    defaults: dict[str, object] = {
        "Publication ID": "PUB",
        "Faculty Name": "Faculty One",
        "Original Faculty Name": "Faculty One",
        "Mapping Status": "Direct",
        "Publication Type": "Journal",
        "Source Sheet": "Journal",
        "Source Row": 2,
        "Original Authors": "Faculty One",
        "First Bold Author": "Faculty One",
        "Author Selection Method": "First Bold Author",
        "Possible Duplicate": "No",
        "Duplicate Classification": "Not Flagged",
        "Duplicate Review Decision": "Not Applicable",
        "Date Status": "Valid",
        "Indexing Raw": "Scopus",
        "Quartile": "Q1",
        "Indexing Recognized": True,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def test_safe_aliases_do_not_increase_unresolved_mapping_count():
    frame = _quality_frame(
        [
            {"Publication ID": "A", "Original Faculty Name": "N. Karuppiah", "Source Row": 2},
            {"Publication ID": "B", "Original Faculty Name": "Karuppiah Natarajan", "Source Row": 3},
            {"Publication ID": "C", "Original Faculty Name": "Natarajan Karuppiah", "Source Row": 4},
            {"Publication ID": "D", "Original Faculty Name": "Dr. N. Karuppiah", "Source Row": 5},
            {"Publication ID": "E", "Original Faculty Name": "karuppiah natarajan", "Source Row": 6},
        ]
    )
    mapped = apply_author_mappings(frame, {})

    assert quality_counts(mapped)["Unresolved author mappings"] == 0
    assert unresolved_mapping_table(mapped).empty


def test_mapped_variant_does_not_count_as_unmapped():
    frame = _quality_frame(
        [{"Original Faculty Name": "P. Balachandran", "Faculty Name": "P. Balachandran"}]
    )
    mapped = apply_author_mappings(frame, {"P. Balachandran": "Praveen Kumar Balachandran"})

    assert quality_counts(mapped)["Unmapped author records"] == 0
    assert unmapped_records_table(mapped).empty


def test_truly_unresolved_publication_counts_as_one_unmapped_row():
    frame = _quality_frame(
        [
            {
                "Faculty Name": UNMAPPED,
                "Original Faculty Name": UNMAPPED,
                "Mapping Status": "Unmapped",
                "Original Authors": "External One; External Two",
                "First Bold Author": "",
                "Author Selection Method": "Unmapped / Review Required",
            }
        ]
    )

    assert quality_counts(frame)["Unmapped author records"] == 1
    assert len(unmapped_records_table(frame)) == 1


def test_unresolved_kpi_counts_distinct_ambiguous_identity_not_publication_rows():
    frame = _quality_frame(
        [
            {
                "Publication ID": f"A{row}",
                "Faculty Name": "A. Rama Krishna",
                "Original Faculty Name": "A. Rama Krishna",
                "Source Row": row,
            }
            for row in range(2, 5)
        ]
        + [
            {
                "Publication ID": f"B{row}",
                "Faculty Name": "A. Ramakrishna",
                "Original Faculty Name": "A. Ramakrishna",
                "Source Row": row,
            }
            for row in range(5, 8)
        ]
    )

    table = unresolved_mapping_table(frame)
    assert quality_counts(frame)["Unresolved author mappings"] == 1
    assert len(table) == 1
    assert table.iloc[0]["Occurrence count"] == 6


def test_duplicate_and_missing_quartile_counts_are_unchanged():
    frame = _quality_frame(
        [
            {
                "Publication ID": "DUP",
                "Possible Duplicate": "Yes",
                "Duplicate Classification": "Review Required",
                "Duplicate Review Decision": "Unreviewed",
                "Quartile": "",
            },
            {"Publication ID": "OK", "Source Row": 3},
        ]
    )

    counts = quality_counts(frame)
    assert counts["Possible duplicate rows"] == 1
    assert counts["Duplicate review required"] == 1
    assert counts["Missing journal quartiles"] == 1
