from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path


DEFAULT_WORKBOOK_PATH = Path(__file__).resolve().parents[1] / "data" / "current_workbook.xlsx"
DEFAULT_METADATA_PATH = Path(__file__).resolve().parents[1] / "data" / "current_workbook.json"


def save_workbook(
    file_bytes: bytes,
    file_name: str,
    workbook_path: Path = DEFAULT_WORKBOOK_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> dict[str, str]:
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(file_bytes).hexdigest()
    metadata = {"name": file_name, "hash": digest, "uploaded_at": datetime.now().astimezone().isoformat()}
    workbook_temp = workbook_path.with_suffix(".tmp")
    metadata_temp = metadata_path.with_suffix(".tmp")
    workbook_temp.write_bytes(file_bytes)
    workbook_temp.replace(workbook_path)
    metadata_temp.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    metadata_temp.replace(metadata_path)
    return metadata


def load_workbook(
    workbook_path: Path = DEFAULT_WORKBOOK_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> tuple[bytes, dict[str, str]] | None:
    try:
        file_bytes = workbook_path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            return None
        return file_bytes, {
            "name": str(metadata["name"]),
            "hash": str(metadata["hash"]),
            "uploaded_at": str(metadata["uploaded_at"]),
        }
    except (FileNotFoundError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return None


def clear_workbook(
    workbook_path: Path = DEFAULT_WORKBOOK_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> None:
    for path in (workbook_path, metadata_path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass