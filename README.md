# 中国地级市科技政策文件爬取 MVP

首个适配站点：济南市科学技术局（[jnsti.jinan.gov.cn](https://jnsti.jinan.gov.cn/)）。

当前 MVP 可以：

- 读取济南市科技局“济南市政策法规”和“规范性文件”公开栏目；
- 调用网站公开列表接口，分页发现文章；
- 按科技创新平台相关关键词筛选；
- 按发布日期从新到旧检查文章，只下载 PDF 附件；
- 按技术创新中心、重点实验室、创新平台、研发机构、科技成果转化、科技计划项目等主题词筛选；
- 默认下载 10 份，支持调整到 10–20 份；
- 将 PDF 平铺保存到省份/城市目录，不再按年份创建文件夹；
- 在 `data/metadata.jsonl` 记录来源 URL、发布日期、文件大小和 SHA-256；
- 通过配置文件为后续地级市适配器预留入口。

## 快速开始

在 PowerShell 中：

```powershell
cd D:\gov-policy-crawler-mvp
uv sync --extra dev
uv run pytest
uv run python -m gov_policy_crawler --list-only
uv run python -m gov_policy_crawler
```

下载结果位于：

```text
D:\gov-policy-crawler-mvp\data\downloads\山东省\济南市\*.pdf
D:\gov-policy-crawler-mvp\data\metadata.jsonl
```

## 常用参数

```powershell
# 下载最新 10 份 PDF（默认行为）
uv run python -m gov_policy_crawler --max-pdfs 10

# 下载最新 20 份 PDF
uv run python -m gov_policy_crawler --max-pdfs 20

# 只采集政策法规和规范性文件，不查工作通知
uv run python -m gov_policy_crawler --no-notices

# 只列出候选文章，不下载
uv run python -m gov_policy_crawler --list-only

# 放慢请求速度
uv run python -m gov_policy_crawler --delay 2
```

## 设计取舍

首版使用 `httpx + BeautifulSoup`，因为济南市科技局的政策列表与 PDF 下载链接都能通过公开 HTTP 接口稳定获取。对于必须依赖 JavaScript、验证码或复杂交互的网站，后续再添加 Playwright 适配器；AI Browser Agent 更适合做网站侦察和生成规则，不适合在首版中逐页驱动浏览器。

请遵守目标网站的公开规则，保持低频请求，不绕过登录、验证码或访问限制；仅采集公开信息，并根据实际用途核对版权、使用条款和数据合规要求。

## 参考仓库

见 [docs/references.md](docs/references.md)。本项目保留了本地参考仓库，但不会直接 vendor 第三方源码。
