from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import posixpath
import re
from typing import Iterable
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"x": MAIN_NS, "r": REL_NS}


@dataclass(frozen=True)
class TextRun:
    text: str
    bold: bool
    start: int
    end: int


@dataclass(frozen=True)
class RichCell:
    text: str
    runs: tuple[TextRun, ...]


def _is_bold(properties: ET.Element | None) -> bool:
    if properties is None:
        return False
    element = properties.find("x:b", NS)
    if element is None:
        return False
    value = element.get("val")
    return value is None or value.lower() not in {"0", "false", "off", "no"}


def _rich_container(container: ET.Element | None) -> RichCell:
    if container is None:
        return RichCell("", ())
    rich_runs = container.findall("x:r", NS)
    raw: list[tuple[str, bool]] = []
    if rich_runs:
        for run in rich_runs:
            text = "".join(node.text or "" for node in run.findall("x:t", NS))
            raw.append((text, _is_bold(run.find("x:rPr", NS))))
    else:
        text = "".join(node.text or "" for node in container.findall("x:t", NS))
        raw.append((text, False))
    position = 0
    runs: list[TextRun] = []
    for text, bold in raw:
        runs.append(TextRun(text, bold, position, position + len(text)))
        position += len(text)
    return RichCell("".join(text for text, _ in raw), tuple(runs))


def _workbook_sheet_paths(archive: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets: dict[str, str] = {}
    for rel in relationships.findall(f"{{{PKG_REL_NS}}}Relationship"):
        target = rel.get("Target", "").replace("\\", "/")
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target.lstrip("./")
        targets[rel.get("Id", "")] = posixpath.normpath(target)
    result: dict[str, str] = {}
    sheets = workbook.find("x:sheets", NS)
    if sheets is not None:
        for sheet in sheets.findall("x:sheet", NS):
            rel_id = sheet.get(f"{{{REL_NS}}}id", "")
            if rel_id in targets:
                result[sheet.get("name", "")] = targets[rel_id]
    return result


def read_rich_cells(xlsx: bytes | bytearray | BytesIO) -> dict[str, dict[str, RichCell]]:
    """Return rich text for every string cell, keyed by sheet name and coordinate."""
    source = BytesIO(bytes(xlsx)) if isinstance(xlsx, (bytes, bytearray)) else xlsx
    try:
        with ZipFile(source) as archive:
            shared: list[RichCell] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [_rich_container(item) for item in root.findall("x:si", NS)]
            result: dict[str, dict[str, RichCell]] = {}
            for sheet_name, path in _workbook_sheet_paths(archive).items():
                root = ET.fromstring(archive.read(path))
                cells: dict[str, RichCell] = {}
                for cell in root.findall(".//x:c", NS):
                    coordinate = cell.get("r", "")
                    cell_type = cell.get("t")
                    rich: RichCell | None = None
                    if cell_type == "s":
                        value = cell.findtext("x:v", default="", namespaces=NS)
                        if value.isdigit() and int(value) < len(shared):
                            rich = shared[int(value)]
                    elif cell_type == "inlineStr":
                        rich = _rich_container(cell.find("x:is", NS))
                    elif cell_type == "str":
                        value = cell.findtext("x:v", default="", namespaces=NS)
                        rich = RichCell(value, (TextRun(value, False, 0, len(value)),))
                    if rich is not None:
                        cells[coordinate] = rich
                result[sheet_name] = cells
            return result
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError(f"The uploaded file is not a readable XLSX workbook: {exc}") from exc


_AUTHOR_SEPARATORS = re.compile(r"\s*(?:\r?\n|;|\||\s+and\s+|\s*&\s*)\s*", re.IGNORECASE)


def _clean_author(value: str) -> str:
    value = re.sub(r"^[\s,;|:&.\-]+|[\s,;|:&\-]+$", "", value)
    value = re.sub(r"^\s*\d+\s*[.)-]\s*", "", value)
    return re.sub(r"\s+", " ", value).strip()


def first_bold_author(cell: RichCell | None) -> str | None:
    """Extract the first author segment that contains bold formatting."""
    if cell is None or not cell.text:
        return None
    bold_run = next((run for run in cell.runs if run.bold and run.text.strip()), None)
    if bold_run is None:
        return None

    # Prefer the complete bold run(s); Excel commonly stores one author per run.
    bold_parts: list[str] = []
    started = False
    for run in cell.runs:
        if run is bold_run:
            started = True
        if started and run.bold:
            bold_parts.append(run.text)
        elif started:
            break
    raw_candidate = "".join(bold_parts)
    # Some source cells split formatting in the middle of a word (for example
    # a plain "P" followed by bold "raveen Kumar..."). Recover that character.
    if raw_candidate[:1].islower() and bold_run.start > 0 and cell.text[bold_run.start - 1].isalpha():
        raw_candidate = cell.text[bold_run.start - 1] + raw_candidate
    if _AUTHOR_SEPARATORS.search(raw_candidate):
        first_segment = next((part for part in _AUTHOR_SEPARATORS.split(raw_candidate) if _clean_author(part)), "")
        candidate = _clean_author(first_segment)
    else:
        candidate = _clean_author(raw_candidate)
    if candidate:
        return candidate

    # If formatting covers only part of a name, recover its surrounding author segment.
    boundaries = [0]
    for match in _AUTHOR_SEPARATORS.finditer(cell.text):
        boundaries.extend([match.start(), match.end()])
    boundaries.append(len(cell.text))
    starts = [point for point in boundaries if point <= bold_run.start]
    ends = [point for point in boundaries if point >= bold_run.end]
    return _clean_author(cell.text[max(starts) if starts else 0 : min(ends) if ends else len(cell.text)]) or candidate or None


def looks_like_single_author(text: str | None) -> bool:
    if not text or not str(text).strip():
        return False
    value = str(text).strip()
    if _AUTHOR_SEPARATORS.search(value) or "," in value:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z.'-]*", value)
    return 1 <= len(words) <= 5


def first_bold_from_runs(runs: Iterable[tuple[str, bool]]) -> str | None:
    """Small public helper used by tests and integrations."""
    position = 0
    parsed: list[TextRun] = []
    text_parts: list[str] = []
    for text, bold in runs:
        parsed.append(TextRun(text, bold, position, position + len(text)))
        text_parts.append(text)
        position += len(text)
    return first_bold_author(RichCell("".join(text_parts), tuple(parsed)))
