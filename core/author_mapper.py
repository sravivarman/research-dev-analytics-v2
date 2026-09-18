from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Iterable

import pandas as pd

from .normalizer import clean_text


UNMAPPED = "UNMAPPED / REVIEW REQUIRED"
DEFAULT_MAPPING_PATH = Path(__file__).resolve().parents[1] / "config" / "author_mapping.json"
DEFAULT_RESOLUTION_PATH = Path(__file__).resolve().parents[1] / "config" / "unmapped_resolutions.json"


def author_key(value: object) -> str:
    text = re.sub(r"^(?:dr|mr|mrs|ms|prof)\.?\s+", "", clean_text(value), flags=re.IGNORECASE).lower()
    return re.sub(r"[^a-z0-9]", "", text)


def _tokens(value: str) -> list[str]:
    tokens = re.findall(r"[a-z]+", value.lower())
    return [token for token in tokens if token not in {"dr", "mr", "mrs", "ms", "prof", "professor"}]


def _could_match(left: str, right: str) -> bool:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return False
    if sorted(a) == sorted(b):
        return True
    full_a, full_b = {x for x in a if len(x) > 1}, {x for x in b if len(x) > 1}
    if not full_a.intersection(full_b):
        return False
    if len(a) != len(b) or len(a) > 3:
        return False
    # Match initials to expanded names independent of name order.
    initials_a, initials_b = Counter(x[0] for x in a), Counter(x[0] for x in b)
    return initials_a == initials_b


def suggest_mappings(names: Iterable[str]) -> dict[str, str]:
    occurrences = Counter(clean_text(name) for name in names if clean_text(name) and clean_text(name) != UNMAPPED)
    observed = sorted(occurrences)
    parent = list(range(len(observed)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i, left in enumerate(observed):
        for j in range(i + 1, len(observed)):
            if _could_match(left, observed[j]):
                union(i, j)
    groups: dict[int, list[str]] = {}
    for index, name in enumerate(observed):
        groups.setdefault(find(index), []).append(name)

    def quality(name: str) -> tuple[int, int, int, int, int, str]:
        tokens = _tokens(name)
        capitalization = sum(part[:1].isupper() for part in re.findall(r"[A-Za-z]+", name))
        honorific = int(bool(re.match(r"^(?:dr|mr|mrs|ms|prof)\.?\s+", name, flags=re.IGNORECASE)))
        return (sum(len(token) > 1 for token in tokens), occurrences[name], capitalization, -honorific, len(name), name)

    result: dict[str, str] = {}
    for members in groups.values():
        canonical = max(members, key=quality)
        for member in members:
            result[member] = canonical
    return result


def load_mapping(path: Path = DEFAULT_MAPPING_PATH) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {clean_text(k): clean_text(v) for k, v in data.items() if clean_text(k) and clean_text(v)}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_mapping(mapping: dict[str, str], path: Path = DEFAULT_MAPPING_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {clean_text(k): clean_text(v) for k, v in mapping.items() if clean_text(k) and clean_text(v)}
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(dict(sorted(cleaned.items())), indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def load_row_resolutions(path: Path = DEFAULT_RESOLUTION_PATH) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(key): clean_text(value) for key, value in data.items() if clean_text(value) and clean_text(value) != UNMAPPED}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_row_resolutions(resolutions: dict[str, str], path: Path = DEFAULT_RESOLUTION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {
        str(key): clean_text(value)
        for key, value in resolutions.items()
        if clean_text(value) and clean_text(value) != UNMAPPED
    }
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(dict(sorted(cleaned.items())), indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def apply_author_mappings(frame: pd.DataFrame, saved: dict[str, str] | None = None) -> pd.DataFrame:
    result = frame.copy()
    saved = saved or {}
    observed = result.loc[result["Original Faculty Name"] != UNMAPPED, "Original Faculty Name"].dropna().astype(str)
    suggested = suggest_mappings(observed)

    def resolve(name: object) -> tuple[str, str]:
        original = clean_text(name)
        if not original or original == UNMAPPED:
            return UNMAPPED, "Unmapped"
        if original in saved:
            return saved[original], "User mapped"
        exact_key = author_key(original)
        for key, canonical in saved.items():
            if author_key(key) == exact_key:
                return canonical, "User mapped"
        canonical = suggested.get(original, original)
        return canonical, "Auto-normalized" if canonical != original else "Direct"

    resolved = result["Original Faculty Name"].map(resolve)
    result["Faculty Name"] = resolved.map(lambda item: item[0])
    result["Mapping Status"] = resolved.map(lambda item: item[1])
    return result


def apply_row_resolutions(frame: pd.DataFrame, resolutions: dict[str, str] | None = None) -> pd.DataFrame:
    """Apply explicit row-level choices without changing extracted author evidence."""
    result = frame.copy()
    resolutions = resolutions or {}
    for index, row in result[result["Faculty Name"].eq(UNMAPPED)].iterrows():
        canonical = clean_text(resolutions.get(str(row["Publication ID"]), ""))
        if canonical and canonical != UNMAPPED:
            result.at[index, "Faculty Name"] = canonical
            result.at[index, "Mapping Status"] = "Manually resolved"
    return result


def mapping_summary(frame: pd.DataFrame, saved: dict[str, str] | None = None) -> pd.DataFrame:
    mapped = apply_author_mappings(frame, saved)
    grouped = (
        mapped.groupby(["Original Faculty Name", "Faculty Name", "Mapping Status"], dropna=False)
        .agg(
            **{
                "Number of Occurrences": ("Publication ID", "size"),
                "Journal Count": ("Publication Type", lambda s: int((s == "Journal").sum())),
                "Conference Count": ("Publication Type", lambda s: int((s == "Conference").sum())),
            }
        )
        .reset_index()
        .rename(columns={"Original Faculty Name": "Observed Name", "Faculty Name": "Canonical Faculty Name"})
    )
    return grouped
