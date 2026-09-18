from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DEFAULT_DUPLICATE_REVIEW_PATH = Path(__file__).resolve().parents[1] / "config" / "duplicate_review.json"
VALID_DUPLICATE_DECISIONS = {"Include", "Exclude"}


def load_duplicate_decisions(path: Path = DEFAULT_DUPLICATE_REVIEW_PATH) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(value) in VALID_DUPLICATE_DECISIONS}


def save_duplicate_decisions(decisions: dict[str, str], path: Path = DEFAULT_DUPLICATE_REVIEW_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {str(key): str(value) for key, value in decisions.items() if str(value) in VALID_DUPLICATE_DECISIONS}
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(dict(sorted(cleaned.items())), indent=2), encoding="utf-8")
    temp.replace(path)


def apply_duplicate_decisions(frame: pd.DataFrame, decisions: dict[str, str] | None = None) -> pd.DataFrame:
    result = frame.copy()
    decisions = decisions or {}
    result["Duplicate Review Decision"] = result.apply(
        lambda row: decisions.get(str(row["Publication ID"]), "Unreviewed")
        if row["Possible Duplicate"] == "Yes"
        else "Not Applicable",
        axis=1,
    )
    return result
