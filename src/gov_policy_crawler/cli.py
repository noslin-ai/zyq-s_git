from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .crawler import JinanCrawler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="采集济南市科技局最新科技政策 PDF")
    parser.add_argument("--config", type=Path, default=Path("config/sites.json"))
    parser.add_argument("--site", default="jinan-science-bureau")
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--delay", type=float, default=1.0, help="请求之间的间隔秒数")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-pages", type=int, default=10, help="每个栏目最多扫描页数，默认 10")
    parser.add_argument("--max-pdfs", type=int, default=10, help="最多下载 PDF 数量，默认 10")
    parser.add_argument("--no-notices", action="store_true", help="只采集政策法规和规范性文件")
    parser.add_argument("--all", action="store_true", dest="include_all", help="不按关键词过滤")
    parser.add_argument("--list-only", action="store_true", help="只列出匹配结果，不下载")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    keywords, sites = load_config(args.config)
    if args.site not in sites:
        raise SystemExit(f"未找到站点配置 {args.site!r}，可选值: {', '.join(sites)}")
    site = sites[args.site]
    crawler = JinanCrawler(
        site=site,
        keywords=keywords,
        output_root=args.output,
        delay=args.delay,
        timeout=args.timeout,
    )
    try:
        stats = crawler.run(
            include_notices=not args.no_notices,
            include_all=args.include_all,
            max_pages=args.max_pages,
            max_pdfs=args.max_pdfs,
            list_only=args.list_only,
        )
    finally:
        crawler.close()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
