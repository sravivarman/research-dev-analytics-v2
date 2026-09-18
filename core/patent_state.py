from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .normalizer import clean_text
from .patent_parser import PATENT_ATTRIBUTION_COLUMNS


DEFAULT_ATTRIBUTION_RESOLUTION_PATH = Path(__file__).resolve().parents[1] / "config" / "patent_attribution_resolutions.json"
DEFAULT_PATENT_DUPLICATE_PATH = Path(__file__).resolve().parents[1] / "config" / "patent_duplicate_review.json"
VALID_DUPLICATE_DECISIONS = {"Include", "Exclude"}


def load_patent_attribution_resolutions(path: Path = DEFAULT_ATTRIBUTION_RESOLUTION_PATH) -> dict[str, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return {
        str(patent_id): [clean_text(name) for name in names if clean_text(name)]
        for patent_id, names in data.items()
        if isinstance(names, list) and any(clean_text(name) for name in names)
    }


def save_patent_attribution_resolutions(
    resolutions: dict[str, list[str]], path: Path = DEFAULT_ATTRIBUTION_RESOLUTION_PATH
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {
        str(patent_id): sorted({clean_text(name) for name in names if clean_text(name)})
        for patent_id, names in resolutions.items()
        if any(clean_text(name) for name in names)
    }
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(dict(sorted(cleaned.items())), indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def apply_patent_attribution_resolutions(
    master: pd.DataFrame,
    attribution: pd.DataFrame,
    resolutions: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result_master, result_attribution = master.copy(), attribution.copy()
    resolutions = resolutions or {}
    replacement_rows: list[dict[str, object]] = []
    resolved_ids: set[str] = set()
    for patent_id, names in resolutions.items():
        if patent_id not in set(result_master["Patent_ID"]):
            continue
        clean_names = [clean_text(name) for name in names if clean_text(name)]
        if not clean_names:
            continue
        source_row = int(result_master.loc[result_master["Patent_ID"].eq(patent_id), "Source_Row"].iloc[0])
        resolved_ids.add(patent_id)
        for order, name in enumerate(dict.fromkeys(clean_names), start=1):
            replacement_rows.append(
                {
                    "Patent_ID": patent_id,
                    "Faculty_Name": name,
                    "Original_Extracted_Name": name,
                    "Canonical_Faculty_Name": name,
                    "Mapping_Status": "Manually Resolved",
                    "Attribution_Method": "Manual Multi-Faculty Resolution",
                    "Bold_Order": order,
                    "Source_Row": source_row,
                    "Faculty_Patent_Credit": 1,
                }
            )
    if resolved_ids:
        result_attribution = result_attribution[~result_attribution["Patent_ID"].isin(resolved_ids)]
        result_attribution = pd.concat(
            [result_attribution, pd.DataFrame(replacement_rows, columns=PATENT_ATTRIBUTION_COLUMNS)],
            ignore_index=True,
        )
        result_master.loc[result_master["Patent_ID"].isin(resolved_ids), "Attribution_Status"] = "Manually Resolved"

    review_ids = set(
        result_attribution.loc[result_attribution["Mapping_Status"].eq("Review Required"), "Patent_ID"]
    )
    unresolved_source = result_master["Patent_Attribution_Method"].eq("No Bold / Multiple People")
    unresolved_ids = set(result_master.loc[unresolved_source, "Patent_ID"]) - resolved_ids
    result_master.loc[result_master["Patent_ID"].isin(review_ids | unresolved_ids), "Attribution_Status"] = "REVIEW REQUIRED"
    return result_master, result_attribution[PATENT_ATTRIBUTION_COLUMNS]


def load_patent_duplicate_decisions(path: Path = DEFAULT_PATENT_DUPLICATE_PATH) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(value) in VALID_DUPLICATE_DECISIONS}


def save_patent_duplicate_decisions(
    decisions: dict[str, str], path: Path = DEFAULT_PATENT_DUPLICATE_PATH
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {str(key): str(value) for key, value in decisions.items() if str(value) in VALID_DUPLICATE_DECISIONS}
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(dict(sorted(cleaned.items())), indent=2), encoding="utf-8")
    temp.replace(path)


def apply_patent_duplicate_decisions(
    master: pd.DataFrame, decisions: dict[str, str] | None = None
) -> pd.DataFrame:
    result = master.copy()
    decisions = decisions or {}
    result["Patent_Duplicate_Review_Decision"] = result.apply(
        lambda row: decisions.get(str(row["Patent_ID"]), "Unreviewed")
        if row["Possible_Patent_Duplicate"] == "Yes"
        else "Not Applicable",
        axis=1,
    )
    return result
