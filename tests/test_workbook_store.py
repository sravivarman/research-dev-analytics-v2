from pathlib import Path

from core.workbook_store import clear_workbook, load_workbook, save_workbook


def test_workbook_store_replaces_and_clears_latest_upload(tmp_path: Path):
    workbook_path = tmp_path / "data" / "current.xlsx"
    metadata_path = tmp_path / "data" / "current.json"

    save_workbook(b"first", "first.xlsx", workbook_path, metadata_path)
    stored = load_workbook(workbook_path, metadata_path)
    assert stored is not None
    assert stored[0] == b"first"

    save_workbook(b"second", "second.xlsx", workbook_path, metadata_path)
    stored = load_workbook(workbook_path, metadata_path)
    assert stored is not None
    assert stored[0] == b"second"
    assert stored[1]["name"] == "second.xlsx"

    clear_workbook(workbook_path, metadata_path)
    assert load_workbook(workbook_path, metadata_path) is None