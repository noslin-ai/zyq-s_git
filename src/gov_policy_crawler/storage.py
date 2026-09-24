from __future__ import annotations

import json
import re
from pathlib import Path


def safe_filename(value: str, max_length: int = 120) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(".")
    value = re.sub(r"\s+", " ", value)
    return (value or "untitled")[:max_length].rstrip(".") or "untitled"

class LocalStorage:
    def __init__(self, root: Path, province: str, city: str) -> None:
        self.root = root
        self.province = province
        self.city = city
        self.download_root = root / "downloads" / province / city
        self.metadata_path = root / "metadata.jsonl"
        self.download_root.mkdir(parents=True, exist_ok=True)

    def next_pdf_path(self, article_title: str, sequence: int = 1) -> Path:
        base = safe_filename(article_title, 120)
        candidate = self.download_root / f"{base}.pdf" if sequence == 1 else self.download_root / f"{base}_{sequence}.pdf"
        while candidate.exists():
            sequence += 1
            candidate = self.download_root / f"{base}_{sequence}.pdf"
        return candidate

    def append_metadata(self, record: dict) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
