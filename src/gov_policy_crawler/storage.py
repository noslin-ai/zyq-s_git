from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def safe_filename(value: str, max_length: int = 120) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(".")
    value = re.sub(r"\s+", " ", value)
    return (value or "untitled")[:max_length].rstrip(".") or "untitled"



def article_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


class LocalStorage:
    def __init__(self, root: Path, province: str, city: str) -> None:
        self.root = root
        self.province = province
        self.city = city
        self.download_root = root / "downloads"
        self.metadata_path = root / "metadata.jsonl"
        self.download_root.mkdir(parents=True, exist_ok=True)

    def article_dir(self, title: str, url: str, published_at: str | None) -> Path:
        year = (published_at or "unknown")[:4]
        folder = self.download_root / self.province / self.city / year
        folder = folder / f"{safe_filename(title, 100)}__{article_key(url)}"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save_article(self, folder: Path, html: str, content: str) -> tuple[str, str]:
        html_path = folder / "article.html"
        text_path = folder / "content.txt"
        html_path.write_text(html, encoding="utf-8")
        text_path.write_text(content, encoding="utf-8")
        return str(html_path), str(text_path)

    def append_metadata(self, record: dict) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
