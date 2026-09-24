# 参考项目

本项目的通用思路参考了以下公开仓库，实际实现针对济南市科技局网站的公开栏目 API 做了独立适配：

- [evian999/crawl_guangxi_gov_docs](https://github.com/evian999/crawl_guangxi_gov_docs)：中国政府网站多地区采集、列表解析、地区配置化。
- [SuperJJ2333/Crawler_of_China_govern_website](https://github.com/SuperJJ2333/Crawler_of_China_govern_website)：上一个仓库的上游项目。
- [microsoft/playwright-python](https://github.com/microsoft/playwright-python)：后续遇到必须执行 JavaScript 或浏览器下载时可作为增强层。

本地参考仓库位于 `references/crawl_guangxi_gov_docs/`，并被 `.gitignore` 排除，不直接把第三方源码 vendor 进本项目。

