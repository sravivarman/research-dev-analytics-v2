from __future__ import annotations

from itertools import combinations
import re

import pandas as pd

from .author_mapper import UNMAPPED
from .normalizer import clean_text, normalized_key


UNMAPPED_HELP = (
    "Publication rows for which no credited faculty can be determined after automatic normalization "
    "and saved manual resolutions."
)
UNRESOLVED_HELP = (
    "Distinct ambiguous author identities requiring human confirmation. Routine spelling/name-format "
    "variants already normalized are excluded."
)


def _identity_tokens(value: object) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z]+", clean_text(value).lower())
        if token not in {"dr", "mr", "mrs", "ms", "prof", "professor"}
    ]


def _ambiguity_reason(left: str, right: str) -> str | None:
    """Identify only cross-canonical name collisions that need human review."""
    left_tokens, right_tokens = _identity_tokens(left), _identity_tokens(right)
    if not left_tokens or not right_tokens:
        return None
    # Capitalization, punctuation, honorifics and reordered forms already assigned
    # to one final canonical identity never reach this cross-canonical comparison.
    if normalized_key(left) == normalized_key(right) and left_tokens != right_tokens:
        return "Same normalized name but different word boundaries; identity confirmation is required."
    left_set, right_set = set(left_tokens), set(right_tokens)
    if min(len(left_tokens), len(right_tokens)) >= 2 and (
        left_set < right_set or right_set < left_set
    ):
        return "One observed identity is contained in a longer distinct canonical name."
    return None


def unresolved_mapping_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Return one row per distinct cross-canonical ambiguous identity group."""
    columns = [
        "Observed Variant",
        "Proposed / possible canonical faculty",
        "Occurrence count",
        "Source rows",
        "Reason review is required",
    ]
    resolved = frame.loc[
        frame["Faculty Name"].notna() & frame["Faculty Name"].ne(UNMAPPED)
    ].copy()
    canonicals = sorted(clean_text(value) for value in resolved["Faculty Name"].unique() if clean_text(value))
    if len(canonicals) < 2:
        return pd.DataFrame(columns=columns)

    parents = {name: name for name in canonicals}
    reasons: dict[tuple[str, str], str] = {}

    def find(name: str) -> str:
        while parents[name] != name:
            parents[name] = parents[parents[name]]
            name = parents[name]
        return name

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left, right in combinations(canonicals, 2):
        reason = _ambiguity_reason(left, right)
        if reason:
            union(left, right)
            reasons[(left, right)] = reason

    groups: dict[str, list[str]] = {}
    for canonical in canonicals:
        groups.setdefault(find(canonical), []).append(canonical)

    rows: list[dict[str, object]] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        group_rows = resolved[resolved["Faculty Name"].isin(members)]
        observed = sorted(
            clean_text(value)
            for value in group_rows["Original Faculty Name"].dropna().unique()
            if clean_text(value) and clean_text(value) != UNMAPPED
        )
        source_rows = sorted(
            {
                f"{source_sheet}:{int(source_row)}"
                for source_sheet, source_row in zip(
                    group_rows["Source Sheet"], group_rows["Source Row"], strict=True
                )
            }
        )
        group_reasons = {
            reason
            for (left, right), reason in reasons.items()
            if left in members and right in members
        }
        rows.append(
            {
                "Observed Variant": " | ".join(observed),
                "Proposed / possible canonical faculty": " | ".join(sorted(members)),
                "Occurrence count": len(group_rows),
                "Source rows": ", ".join(source_rows),
                "Reason review is required": " ".join(sorted(group_reasons)),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def unmapped_records_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Trace records whose final, post-resolution faculty remains unmapped."""
    columns = [
        "Source Sheet",
        "Source Row",
        "Original Authors",
        "Extracted First Bold Author",
        "Current Faculty",
        "Reason",
    ]
    unresolved = frame.loc[frame["Faculty Name"].eq(UNMAPPED)].copy()
    if unresolved.empty:
        return pd.DataFrame(columns=columns)

    def reason(row: pd.Series) -> str:
        if not clean_text(row.get("First Bold Author")) and row.get("Author Selection Method") == "Unmapped / Review Required":
            return "No bold author was detected in a multi-author cell, and no saved row resolution applies."
        return "The extracted author remains unmapped after automatic normalization and saved resolutions."

    unresolved["Reason"] = unresolved.apply(reason, axis=1)
    return unresolved[
        ["Source Sheet", "Source Row", "Original Authors", "First Bold Author", "Faculty Name", "Reason"]
    ].rename(
        columns={
            "First Bold Author": "Extracted First Bold Author",
            "Faculty Name": "Current Faculty",
        }
    )


def quality_counts(frame: pd.DataFrame) -> dict[str, int]:
    journal = frame["Publication Type"].eq("Journal")
    unmapped = unmapped_records_table(frame)
    unresolved = unresolved_mapping_table(frame)
    return {
        "Total source records": len(frame),
        "Successfully mapped records": len(frame) - len(unmapped),
        "Unmapped author records": len(unmapped),
        "Unresolved author mappings": len(unresolved),
        "No-bold fallback records": int(frame["Author Selection Method"].eq("No Bold / Single Author").sum()),
        "Possible duplicate rows": int(frame["Possible Duplicate"].eq("Yes").sum()),
        "Strong duplicate rows": int(frame["Duplicate Classification"].eq("Strong Duplicate").sum()),
        "Duplicate review required": int(frame["Duplicate Classification"].eq("Review Required").sum()),
        "User-excluded duplicate rows": int(frame.get("Duplicate Review Decision", pd.Series(index=frame.index, dtype=str)).eq("Exclude").sum()),
        "Missing dates": int(frame["Date Status"].eq("Missing").sum()),
        "Invalid dates": int(frame["Date Status"].eq("Invalid").sum()),
        "Missing indexing values": int(frame["Indexing Raw"].fillna("").eq("").sum()),
        "Missing journal quartiles": int((journal & frame["Quartile"].fillna("").eq("")).sum()),
        "Unrecognized indexing labels": int((~frame["Indexing Recognized"].astype(bool)).sum()),
    }


def quality_tables(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    source = ["Source Sheet", "Source Row", "Title", "Original Authors"]
    return {
        "Unmapped Records": unmapped_records_table(frame),
        "Unresolved Mappings": unresolved_mapping_table(frame),
        "Possible Duplicates": frame.loc[
            frame["Possible Duplicate"].eq("Yes"),
            ["Publication ID", "Duplicate Classification", "Duplicate Reason", "Duplicate Review Decision", "Duplicate Key",
             "Faculty Name", "Calendar Year", "Publication Type", "Title", "DOI", "Source Sheet", "Source Row"],
        ],
        "Missing / Invalid Dates": frame.loc[
            frame["Date Status"].isin(["Missing", "Invalid"]),
            ["Date Status", "Faculty Name", "Publication Type", "Title", "Source Sheet", "Source Row"],
        ],
        "Unrecognized Indexing": frame.loc[
            ~frame["Indexing Recognized"].astype(bool),
            ["Indexing Raw", "Faculty Name", "Title", "Source Sheet", "Source Row"],
        ],
        "Rows with No Bold Author": frame.loc[
            ~frame["Author Selection Method"].eq("First Bold Author"), source + ["Author Selection Method"]
        ],
    }
