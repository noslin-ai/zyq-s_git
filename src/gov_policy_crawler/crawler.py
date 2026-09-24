from __future__ import annotations

import math
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .models import Article, ArticleSummary, Attachment, ColumnConfig, SiteConfig
from .storage import LocalStorage, safe_filename


API_PATH = "/api-gateway/jpaas-publish-server/front/page/build/unit"
PAGE_SIZE = 15


def _clean_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def _date_from_text(value: str) -> str | None:
    match = re.search(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})", value)
    if not match:
        return None
    return match.group(1).replace("/", "-").replace(".", "-")


def _filename_from_url(url: str, fallback: str) -> str:
    filename = parse_qs(urlparse(url).query).get("fileName", [""])[0]
    filename = unquote(filename).strip()
    if filename:
        return safe_filename(filename)
    path_name = unquote(Path(urlparse(url).path).name).strip()
    if re.search(r"\.(pdf|doc|docx|xls|xlsx|zip)$", path_name, re.I):
        return safe_filename(path_name)
    return safe_filename(fallback)


def parse_list_html(
    html: str,
    base_url: str,
    column: ColumnConfig,
) -> tuple[list[ArticleSummary], int]:
    soup = BeautifulSoup(html, "html.parser")
    pagination = soup.select_one(".pagination")
    count = int(pagination.get("count", "0")) if pagination else 0
    summaries: list[ArticleSummary] = []
    for link in soup.select(".page-content li a[href]"):
        title = (link.get("title") or link.get_text(" ", strip=True)).strip()
        href = link.get("href", "").strip()
        if not title or not href or href.startswith(("#", "javascript:")):
            continue
        date_text = link.find_next("span").get_text(" ", strip=True) if link.find_next("span") else ""
        summaries.append(
            ArticleSummary(
                title=title,
                url=urljoin(base_url + "/", href),
                published_at=_date_from_text(date_text),
                column_id=column.id,
                column_name=column.name,
                column_kind=column.kind,
            )
        )
    return summaries, count


def parse_article_html(
    html: str,
    url: str,
    summary: ArticleSummary,
) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    title_meta = soup.select_one('meta[name="ArticleTitle"]')
    date_meta = soup.select_one('meta[name="PubDate"]')
    title = (title_meta.get("content") if title_meta else None) or summary.title
    # The list page is the stable public index for this site. Some detail pages
    # expose stale or inconsistent PubDate metadata, so prefer the list date.
    published_at = summary.published_at or _date_from_text(date_meta.get("content", "") if date_meta else "")

    content_root = (
        soup.select_one(".dfnr")
        or soup.select_one("#zoom")
        or soup.select_one(".TRS_Editor")
        or soup.body
        or soup
    )
    content_soup = BeautifulSoup(str(content_root), "html.parser")
    for node in content_soup.select("script, style, noscript"):
        node.decompose()
    content = _clean_text(content_soup.get_text("\n"))

    attachments: list[Attachment] = []
    seen: set[str] = set()
    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        absolute_url = urljoin(url, href)
        is_download = "/document/download" in absolute_url or bool(
            re.search(r"\.(pdf|doc|docx|xls|xlsx|zip)(?:$|[?#])", absolute_url, re.I)
        )
        if not is_download:
            continue
        filename = _filename_from_url(absolute_url, link.get_text(" ", strip=True) or title)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        attachments.append(Attachment(filename=filename, url=absolute_url))

    return Article(
        summary=summary,
        title=title.strip(),
        url=url,
        published_at=published_at,
        content=content,
        html=html,
        attachments=attachments,
    )


class JinanCrawler:
    def __init__(
        self,
        site: SiteConfig,
        keywords: list[str],
        output_root: Path,
        delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self.site = site
        self.keywords = [item.casefold() for item in keywords if item.strip()]
        self.delay = max(0.0, delay)
        self.last_request_at = 0.0
        request_timeout = min(float(timeout), 20.0)
        self.client = httpx.Client(
            timeout=httpx.Timeout(request_timeout, connect=min(request_timeout, 10.0)),
            follow_redirects=True,
            headers={
                "User-Agent": "gov-policy-crawler-mvp/0.1 (+public-policy-research)",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            },
        )
        self.storage = LocalStorage(output_root, site.province, site.city)

    def close(self) -> None:
        self.client.close()

    def _get(self, url: str, params: dict | None = None, retries: int = 3) -> httpx.Response:
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                self.last_request_at = time.monotonic()
                return response
            except (httpx.HTTPError, OSError) as exc:
                error = exc
                if attempt < retries:
                    time.sleep(min(2.0 * attempt, 5.0))
        raise RuntimeError(f"请求失败: {url}: {error}")

    def list_page(self, column: ColumnConfig, page_no: int) -> tuple[list[ArticleSummary], int]:
        params = {
            "parseType": "bulidstatic",
            "webId": "10",
            "tplSetId": "GbnFskR3C7PD0nABf9KzT",
            "pageType": "column",
            "tagId": "信息列表",
            "editType": "null",
            "pageId": column.id,
            "paramJson": __import__("json").dumps(
                {"pageNo": page_no, "pageSize": PAGE_SIZE}, ensure_ascii=False, separators=(",", ":")
            ),
        }
        response = self._get(self.site.base_url + API_PATH, params=params)
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"列表 API 返回失败: {payload.get('message')}")
        return parse_list_html(payload.get("data", {}).get("html", ""), self.site.base_url, column)

    def iter_summaries(
        self,
        column: ColumnConfig,
        max_pages: int | None = None,
    ):
        first_page, count = self.list_page(column, 1)
        total_pages = max(1, math.ceil(count / PAGE_SIZE))
        page_limit = min(total_pages, max_pages) if max_pages else total_pages
        yield from first_page
        for page_no in range(2, page_limit + 1):
            summaries, _ = self.list_page(column, page_no)
            yield from summaries

    def matches(self, summary: ArticleSummary, include_all: bool = False) -> bool:
        if include_all or not self.keywords:
            return True
        haystack = summary.title.casefold()
        return any(keyword in haystack for keyword in self.keywords)

    def fetch_article(self, summary: ArticleSummary) -> Article:
        response = self._get(summary.url, retries=1)
        return parse_article_html(response.text, summary.url, summary)

    def download_attachment(self, attachment: Attachment, article_title: str, sequence: int) -> dict:
        path = self.storage.next_pdf_path(article_title, sequence)
        digest = hashlib.sha256()
        size = 0
        temp_path = path.with_suffix(path.suffix + ".part")
        response = self._get(attachment.url, retries=2)
        first_bytes = bytearray()
        try:
            with temp_path.open("wb") as handle:
                for chunk in response.iter_bytes(1024 * 64):
                    if len(first_bytes) < 5:
                        first_bytes.extend(chunk[: 5 - len(first_bytes)])
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if not first_bytes.startswith(b"%PDF"):
                raise RuntimeError(f"下载内容不是有效 PDF: {attachment.url}")
            temp_path.replace(path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return {
            "filename": path.name,
            "path": str(path),
            "source_filename": attachment.filename,
            "url": attachment.url,
            "size": size,
            "sha256": digest.hexdigest(),
            "content_type": response.headers.get("content-type"),
        }

    def run(
        self,
        *,
        include_notices: bool = True,
        include_all: bool = False,
        max_pages: int | None = 10,
        max_pdfs: int = 10,
        list_only: bool = False,
    ) -> dict:
        stats = {
            "listed": 0,
            "matched": 0,
            "checked_articles": 0,
            "pdfs": 0,
            "skipped_no_pdf": 0,
            "errors": 0,
        }
        summaries: list[ArticleSummary] = []
        for column in self.site.columns:
            if not column.enabled or (column.kind == "notice" and not include_notices):
                continue
            summaries.extend(self.iter_summaries(column, max_pages=max_pages))

        stats["listed"] = len(summaries)
        candidates = [item for item in summaries if self.matches(item, include_all=include_all)]
        candidates.sort(key=lambda item: item.published_at or "", reverse=True)
        stats["matched"] = len(candidates)
        if list_only:
            for summary in candidates:
                print(f"[match] {summary.published_at or 'unknown'} {summary.title}")
            return stats

        seen_pdf_urls = self._existing_pdf_urls()
        for summary in candidates:
            if stats["pdfs"] >= max_pdfs:
                break
            print(f"[check] {summary.published_at or 'unknown'} {summary.title}")
            try:
                article = self.fetch_article(summary)
                stats["checked_articles"] += 1
                pdfs = [item for item in article.attachments if item.filename.casefold().endswith(".pdf")]
                pdfs = [item for item in pdfs if item.url not in seen_pdf_urls]
                if not pdfs:
                    stats["skipped_no_pdf"] += 1
                    continue
                for sequence, attachment in enumerate(pdfs, start=1):
                    if stats["pdfs"] >= max_pdfs:
                        break
                    seen_pdf_urls.add(attachment.url)
                    record = self.download_attachment(attachment, article.title, sequence)
                    self.storage.append_metadata(
                        {
                            "site_id": self.site.id,
                            "province": self.site.province,
                            "city": self.site.city,
                            "department": self.site.department,
                            "column_id": article.summary.column_id,
                            "column_name": article.summary.column_name,
                            "title": article.title,
                            "published_at": article.published_at,
                            "article_url": article.url,
                            "pdf": record,
                            "crawled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                        }
                    )
                    stats["pdfs"] += 1
            except Exception as exc:  # keep one broken item from stopping the whole crawl
                stats["errors"] += 1
                print(f"[error] {summary.url}: {exc}")
        return stats

    def _existing_pdf_urls(self) -> set[str]:
        seen: set[str] = set()
        if not self.storage.metadata_path.exists():
            return seen
        for line in self.storage.metadata_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            pdf = record.get("pdf", {})
            url = pdf.get("url")
            if url:
                seen.add(url)
        return seen
