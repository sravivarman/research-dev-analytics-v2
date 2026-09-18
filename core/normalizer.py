from __future__ import annotations

from datetime import date, datetime
import hashlib
import re
import unicodedata

import pandas as pd


def clean_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u00a0", " ")).strip()


def normalized_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def normalize_doi(value: object) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"digital\s*object\s*identifier.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpdf\b.*$", "", text, flags=re.IGNORECASE)
    doi = re.search(r"10\.\d{4,9}/[^\s<>\"\]]+", text, flags=re.IGNORECASE)
    if doi:
        return doi.group(0).strip().rstrip(".,; ").lower()
    # Some source "DOI" columns contain publisher/document URLs rather than a DOI.
    # Preserve a normalized URL-like identifier so exact duplicates remain visible.
    text = re.sub(r"^doi\s*:\s*", "", text).strip()
    return text.rstrip("/.,; ")


def parse_year(value: object) -> tuple[int | None, pd.Timestamp | None, str]:
    if value is None or clean_text(value) == "":
        return None, None, "Missing"
    if isinstance(value, (pd.Timestamp, datetime, date)):
        stamp = pd.Timestamp(value)
        return int(stamp.year), stamp, "Valid"
    if isinstance(value, (int, float)) and not pd.isna(value):
        number = float(value)
        if 1900 <= number <= 2200 and number.is_integer():
            return int(number), pd.Timestamp(year=int(number), month=1, day=1), "Valid"
        try:
            stamp = pd.Timestamp("1899-12-30") + pd.to_timedelta(number, unit="D")
            if 1900 <= stamp.year <= 2200:
                return int(stamp.year), stamp, "Valid"
        except (ValueError, OverflowError):
            pass
    text = clean_text(value)
    match = re.search(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)", text)
    if match:
        year = int(match.group(1))
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
        stamp = parsed if not pd.isna(parsed) else pd.Timestamp(year=year, month=1, day=1)
        return year, stamp, "Valid"
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if not pd.isna(parsed) and 1900 <= parsed.year <= 2200:
        return int(parsed.year), parsed, "Valid"
    return None, None, "Invalid"


def indexing_flags(value: object) -> dict[str, object]:
    raw = clean_text(value)
    text = raw.lower()
    non_scopus = bool(re.search(r"\bnon[\s-]*scopus\b|\bnot[\s-]*scopus\b", text))
    scie = bool(re.search(r"\bscie\b", text))
    sci = bool(re.search(r"\bsci\b", text))
    esci = bool(re.search(r"\besci\b", text))
    scopus = bool(re.search(r"\bscopus\b", text)) and not non_scopus
    recognized = sci or scie or esci or scopus or non_scopus or raw == ""
    return {
        "SCI_SCIE_Flag": int(sci or scie),
        "ESCI_Flag": int(esci),
        "Scopus_Flag": int(scopus),
        "Non_Scopus_Flag": int(non_scopus),
        "Indexing Recognized": recognized,
    }


def normalize_quartile(value: object) -> str:
    text = clean_text(value).upper()
    match = re.search(r"\bQ\s*([1-4])\b|\bQUARTILE\s*([1-4])\b", text)
    if not match:
        return ""
    return f"Q{match.group(1) or match.group(2)}"


def publication_id(sheet: str, row: int, title: object, doi: object) -> str:
    seed = f"{sheet}|{row}|{clean_text(title)}|{clean_text(doi)}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12].upper()


def is_complete_doi(value: object) -> bool:
    """Return true only for a DOI with a registrant and non-empty suffix."""
    return bool(re.fullmatch(r"10\.\d{4,9}/\S+", clean_text(value), flags=re.IGNORECASE))


def add_duplicate_flags(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["Normalized DOI"] = result["DOI"].map(normalize_doi)
    result["Normalized Title"] = result["Title"].map(normalized_key)
    result["Possible Duplicate"] = "No"
    result["Duplicate Classification"] = "Not Flagged"
    result["Duplicate Reason"] = ""
    result["Duplicate Key"] = ""
    complete_doi = result["Normalized DOI"].map(is_complete_doi)

    for doi, group in result[complete_doi].groupby("Normalized DOI"):
        if not doi or len(group) < 2:
            continue
        titles = {title for title in group["Normalized Title"] if title}
        strong = len(titles) == 1 and len(titles) > 0
        classification = "Strong Duplicate" if strong else "Review Required"
        reason = "Same complete DOI and normalized title" if strong else "Same complete DOI but different titles"
        result.loc[group.index, ["Possible Duplicate", "Duplicate Classification", "Duplicate Reason", "Duplicate Key"]] = [
            "Yes", classification, reason, f"DOI:{doi}"
        ]

    for title, group in result[result["Normalized Title"] != ""].groupby("Normalized Title"):
        if len(group) < 2:
            continue
        unclassified = group.index[result.loc[group.index, "Duplicate Classification"].eq("Not Flagged")]
        if len(unclassified) == 0:
            continue
        publication_types = set(group["Publication Type"]) if "Publication Type" in group else set()
        reason = (
            "Same normalized title across publication types"
            if len(publication_types) > 1
            else "Same normalized title; review required"
        )
        result.loc[unclassified, ["Possible Duplicate", "Duplicate Classification", "Duplicate Reason", "Duplicate Key"]] = [
            "Yes", "Review Required", reason, f"TITLE:{title}"
        ]
    return result
