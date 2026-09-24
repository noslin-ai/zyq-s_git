from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnConfig:
    id: str
    name: str
    kind: str = "policy"
    enabled: bool = True


@dataclass(frozen=True)
class SiteConfig:
    id: str
    province: str
    city: str
    department: str
    base_url: str
    columns: tuple[ColumnConfig, ...]


@dataclass(frozen=True)
class ArticleSummary:
    title: str
    url: str
    published_at: str | None
    column_id: str
    column_name: str
    column_kind: str


@dataclass
class Article:
    summary: ArticleSummary
    title: str
    url: str
    published_at: str | None
    content: str
    html: str
    attachments: list[Attachment] = field(default_factory=list)


@dataclass(frozen=True)
class Attachment:
    filename: str
    url: str

