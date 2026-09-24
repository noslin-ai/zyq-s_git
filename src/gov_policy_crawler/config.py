from __future__ import annotations

import json
from pathlib import Path

from .models import ColumnConfig, SiteConfig


def load_config(path: Path) -> tuple[list[str], dict[str, SiteConfig]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    keywords = [str(item).strip() for item in raw.get("keywords", []) if str(item).strip()]
    sites: dict[str, SiteConfig] = {}
    for item in raw.get("sites", []):
        columns = tuple(
            ColumnConfig(
                id=str(column["id"]),
                name=str(column["name"]),
                kind=str(column.get("kind", "policy")),
                enabled=bool(column.get("enabled", True)),
            )
            for column in item.get("columns", [])
        )
        site = SiteConfig(
            id=str(item["id"]),
            province=str(item["province"]),
            city=str(item["city"]),
            department=str(item["department"]),
            base_url=str(item["base_url"]).rstrip("/"),
            columns=columns,
        )
        sites[site.id] = site
    return keywords, sites

