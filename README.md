# 🛠️ 我的自动化工具箱 (Automation Toolbox)

这个仓库汇集了我个人常用的脚本和自动化代理工具，主要用于 Web3 数据调研、自动化处理及工程效率提升。

## 📁 仓库结构

* `get_ca_by_doc.py`: 智能 Web3 合约数据抓取代理。
---

## 📄 工具说明

### 1. `get_ca_by_doc.py` - Web3 智能合约地址抓取器

这是一个基于 **Gemini 2.5 Pro** 和 **Playwright** 开发的自主 AI 代理。它能够自动遍历项目技术文档，发现包含合约地址的页面，并进行精准提取和格式化。

#### 核心功能：

* **智能发现**: 自动解析 `sitemap.xml` 或通过 DOM 爬取网页链接，高效锁定高价值文档页面。
* **动态内容处理**: 采用“黑科技”手段强行展开 `<details>` 折叠面板，并遍历页面 Tab 标签，确保页面上的隐藏内容全部可见。
* **严格格式化**: 自动将 Ethereum, BNB Chain 和 Polygon 地址转换为统一小写（确保长度为 42），同时严格保留 Tron (TRX) 地址的原始大小写格式。
* **高鲁棒性**: 内置指数退避重试机制，有效应对网络波动及 API 服务器拥堵。

#### 使用方法：

1. **安装依赖**: 请确保安装了相关库：
```bash
pip install google-generativeai playwright requests
playwright install chromium
```

2. **配置**: 将脚本中的 `API_KEY` 替换为您有效的 Gemini API Key。

3. **设置目标**: 修改 `start_url` 变量为您想要调研的项目文档网址：
```python
start_url = "https://docs.your-target-project.io/"
```

4. **运行**:
```bash
python get_ca_by_doc.py
```

---

## ⚙️ 技术栈与环境要求

* **操作系统**: macOS (推荐，已针对路径处理进行适配)。
* **开发语言**: Python 3.x。
* **核心框架**:
* `google-generativeai` (AI 推理引擎)。
* `playwright` (无头浏览器自动化)。
* `requests` & `xml.etree` (网络请求与网页解析)。

---

## 🤝 贡献与说明

如果您对这些工具有优化建议，欢迎提交 Pull Request。在使用自动化脚本抓取的数据进行后续操作前，请务必进行二次人工核验，以确保数据的准确性。
