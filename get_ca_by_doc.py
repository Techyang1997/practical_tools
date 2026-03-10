import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from playwright.sync_api import sync_playwright
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import time
from google.api_core.exceptions import DeadlineExceeded, InternalServerError

API_KEY = "API-KEY"  # <-- 记得替换这里
start_url = "https://docs.butternetwork.io/" # 要调研的技术文档网址

# ==========================================
# 工具 1：获取网站目录与链接
# ==========================================
def get_website_directory(url: str) -> str:
    print(f"\n🕵️  [Agent 动作]: 正在扫描网站目录树 {url} ...")

    def get_urls_from_sitemap(base_url):
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        print(f"🔎 [策略一] 尝试拉取站点地图: {sitemap_url}")
        try:
            res = requests.get(sitemap_url, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                return [child.text.strip() for child in root.iter() if 'loc' in child.tag and child.text]
        except Exception:
            pass
        return []

    def get_urls_from_dom(base_url):
        print(f"🤖 [策略二] 启动无头浏览器暴力提取: {base_url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            try:
                page.goto(base_url, wait_until="networkidle", timeout=20000)
                links = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a'))
                                .map(a => a.href)
                                .filter(href => href.startsWith('http'));
                }""")
                return links
            except Exception:
                return []
            finally:
                browser.close()

    all_urls = get_urls_from_sitemap(url)
    if not all_urls:
        all_urls = get_urls_from_dom(url)

    if not all_urls:
        return "获取目录失败: 未找到任何可用链接"

    keywords = ['contract', 'address', 'market', 'deployment', 'network', 'environments']
    filtered_urls = list(set([u for u in all_urls if any(kw in u.lower() for kw in keywords)]))

    if not filtered_urls:
        filtered_urls = list(set(all_urls))[:20]

    result_str = "提取到的高价值目录链接如下：\n"
    for link_url in filtered_urls:
        result_str += f"- {link_url}\n"

    print(f"✅  [Agent 返回]: 成功提取并过滤出 {len(filtered_urls)} 个相关链接。")
    return result_str[:30000]


# ==========================================
# 工具 2：读取特定网页正文 (已升级：通杀 Tab 与 Details 折叠面板)
# ==========================================
def get_page_content(url: str) -> str:
    print(f"\n📄  [Agent 动作]: 深入目标页面，正在抓取内容 {url} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            print("🔄  [Agent 动作]: 正在扫描并展开页面上的隐藏内容...")

            # 【黑科技 1】：瞬间强行展开所有的 <details> 折叠面板 (专治 Bungee 这种结构)
            # 这行 JS 会找到页面上所有的 details 标签，并强行给它们加上 open 属性，使其内部文本立刻变得可见
            page.evaluate("""() => {
                document.querySelectorAll('details').forEach(detail => {
                    detail.setAttribute('open', 'true');
                });
            }""")

            # 稍微等半秒，让浏览器渲染出刚被撑开的文本
            page.wait_for_timeout(500)

            # 【黑科技 2】：保留之前应对传统 Tab 的点击逻辑 (为了兼容其他文档)
            all_visible_text = ""
            tabs = page.locator('button[role="tab"], li[role="tab"], .tab, .tabs__item, [class*="tabButton"]')
            tab_count = tabs.count()

            if tab_count > 0:
                print(f"🔍  发现了 {tab_count} 个传统切换标签，正在逐一点击读取...")
                for i in range(tab_count):
                    try:
                        tab = tabs.nth(i)
                        if tab.is_visible():
                            tab.click(timeout=3000)
                            page.wait_for_timeout(1000)

                            if page.locator("main").count() > 0:
                                current_text = page.locator("main").inner_text()
                            else:
                                current_text = page.locator("body").inner_text()

                            all_visible_text += f"\n\n--- [Tab {i + 1} 内容] ---\n" + current_text
                    except Exception:
                        continue
                text_to_process = all_visible_text
            else:
                # 如果没有传统 Tab，说明页面内容(包括刚刚被强行展开的 details)都已经直接可见了
                if page.locator("main").count() > 0:
                    text_to_process = page.locator("main").inner_text()
                else:
                    text_to_process = page.locator("body").inner_text()

            # 清理格式并返回
            cleaned_text = "\n".join([line.strip() for line in text_to_process.split('\n') if line.strip()])
            final_text = cleaned_text[:80000]
            print(f"✅  [Agent 返回]: 成功抓取(含隐藏面板)页面文本，共 {len(final_text)} 字符。")
            return final_text

        except Exception as e:
            return f"获取网页内容失败: {str(e)}"
        finally:
            browser.close()

# ==========================================
# AI Agent 初始化与任务调度
# ==========================================

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(
    model_name='gemini-2.5-pro',
    tools=[get_website_directory, get_page_content]
)

chat = model.start_chat(enable_automatic_function_calling=True)



prompt = f"""
你是一个严谨的 Web3 智能合约数据搜集 Agent。
你的任务是从给定的项目文档首页出发，自主寻找、提取并验证智能合约地址。

初始入口网站：{start_url}

请严格按照以下思维链（Chain of Thought）执行任务：
第一步：调用 get_website_directory 工具，扫描初始入口网站的目录链接。
第二步：仔细分析返回的链接列表，寻找包含 "Contract", "Deployed Contracts", "Markets", "Addresses", "Developer" 等相关字眼的 URL。
第三步：调用 get_page_content 工具，访问你认为有可能包含合约地址的URL,如果相关URL有多个，都要进行提取。如果第一次没找到，可以尝试访问其他候选URL。
第四步：提取页面中的合约信息
【核心要求 - 严禁遗漏，但不重复抓取】：
1. 你必须逐字逐句扫描网页，提取出**Ethereum,BNB Chain,Polygon,Tron四条链所有**的合约地址。
2. 绝对不允许省略、绝对不允许使用“等”、“...”或“省略号”。
3. 即使有 100 个合约，你也要完整输出 100 行。
4. 严格整理成 csv 表格：
- 表头必须为：| 链 | 地址 | 名称 |
- 🚨【地址大小写极度重要规则】：
  1. 对于 Ethereum, BNB Chain, Polygon 链的地址，必须将其统一转换为小写输出，且保证长度为42
  2. 对于 Tron 链的地址，必须完全保持原样（原始大小写），绝对不要做任何大小写转换操作！
请开始你的任务。
"""

print("\n🧠 Agent 已启动，正在直接提取目标网页并验证 (请耐心等待)...\n")

# ==========================================
# 自动重试机制配置
# ==========================================
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 初始等待时间（秒）

for attempt in range(1, MAX_RETRIES + 1):
    try:
        # 尝试发送任务给大模型
        response = chat.send_message(prompt)

        # 如果代码能走到这里，说明成功了！打印结果并跳出循环
        print("\n" + "=" * 50 + "\n🎯 最终提取结果：\n" + "=" * 50 + "\n")
        print(response.text)
        break  # 成功后立刻退出循环

    except (DeadlineExceeded, InternalServerError) as e:
        # 专门捕获 504 超时和 500 服务器错误
        print(f"\n⚠️  [网络波动]: 遭遇大模型服务器超时或拥堵 ({type(e).__name__})。")

        if attempt < MAX_RETRIES:
            print(f"⏳  准备进行第 {attempt}/{MAX_RETRIES} 次重试，休眠 {RETRY_DELAY} 秒让服务器喘口气...")
            time.sleep(RETRY_DELAY)
            RETRY_DELAY *= 2  # 指数退避：第一次等 5 秒，第二次等 10 秒，防止连续高频请求被封
        else:
            print(f"\n❌  [彻底失败]: 已达到最大重试次数 ({MAX_RETRIES}次)。可能该页面过于复杂或服务器当前大面积拥堵。")

    except Exception as e:
        # 捕获其他非网络引起的致命代码错误（直接停止，不重试）
        print(f"\n❌  [致命错误]: 发生未预期的本地异常: {str(e)}")
        break