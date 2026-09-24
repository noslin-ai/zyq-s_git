from pathlib import Path

from gov_policy_crawler.crawler import parse_article_html, parse_list_html
from gov_policy_crawler.models import ArticleSummary, ColumnConfig
from gov_policy_crawler.storage import safe_filename


def test_parse_list_html_extracts_summary_and_count() -> None:
    html = Path("tests/fixtures/list.html").read_text(encoding="utf-8")
    summaries, count = parse_list_html(
        html,
        "https://jnsti.jinan.gov.cn",
        ColumnConfig(id="11686", name="规范性文件"),
    )
    assert count == 12
    assert summaries[0].title.startswith("济南市科学技术局")
    assert summaries[0].published_at == "2023-03-27"
    assert summaries[0].url.endswith("art_11686_4775357.html")


def test_safe_filename_removes_windows_reserved_characters() -> None:
    value = safe_filename('政策:《测试》/附件?.docx')
    assert ":" not in value
    assert "/" not in value
    assert "?" not in value


def test_article_prefers_list_date_and_keeps_direct_file_extension() -> None:
    html = """
    <html>
      <head>
        <meta name="ArticleTitle" content="重点实验室办法">
        <meta name="PubDate" content="2026-04-30 10:00">
      </head>
      <body>
        <div id="zoom">正文内容</div>
        <a href="/cms_files/attach/abc123.pdf">附件</a>
      </body>
    </html>
    """
    summary = ArticleSummary(
        title="重点实验室办法",
        url="https://jnsti.jinan.gov.cn/col/art.html",
        published_at="2025-08-29",
        column_id="11686",
        column_name="规范性文件",
        column_kind="policy",
    )
    article = parse_article_html(html, summary.url, summary)
    assert article.published_at == "2025-08-29"
    assert article.attachments[0].filename.endswith(".pdf")
