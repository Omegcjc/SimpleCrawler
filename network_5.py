import asyncio
import aiohttp
import json
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import whois  # 添加 whois 导入
from pathlib import Path
from ipwhois import IPWhois  # 添加 ipwhois 导入
import dns.resolver  # 添加 DNS 解析导入
from concurrent.futures import ThreadPoolExecutor  # 添加 ThreadPoolExecutor 导入
from collections import defaultdict  # 添加 defaultdict 导入


# 全局简单日志记录（你也可以改成 logging 模块）
def log_error(message: str):
    with open("error.log", "a", encoding="utf-8") as f:
        f.write(message + "\n")

class ResourceAnalyzer:
    """
    负责收集页面加载过程中所有资源信息，
    若检测到视频页面，则自动播放视频并等待播放结束。
    """
    def __init__(self, url, page, platform):
        """
        初始化 ResourceAnalyzer 类。

        :param url: 要分析的页面 URL
        :param page: Playwright 的页面对象
        :param platform: 平台名称，用于标识当前分析的平台
        """
        self.url = url
        self.page = page
        self.platform = platform
        self.responses = []  # 用于存储页面加载过程中所有的响应信息
        self.initiator_map = defaultdict(list)  # 用于存储请求启动链

    # 处理页面加载过程中捕获的响应， 这里的响应是 Playwright 捕获的响应对象
    async def _handle_response(self, response):
        """
        处理页面加载过程中捕获的响应。

        :param response: Playwright 捕获的响应对象
        """
        self.responses.append({
            "response": response
        })

    # 处理页面加载过程中捕获的请求，这里的 initiator 是一个复杂的对象，包含了发起请求的完整链条
    async def _handle_request(self, event):
        url = event["request"]["url"]

        # 保存 initiator 信息（完整结构）
        self.initiator_map[url] = event.get("initiator")

    # 判断当前页面是否为视频页面
    async def _is_video_page(self):
        """
        判断当前页面是否为视频页面。

        :return: 布尔值，表示是否为视频页面
        """
        return await self.page.evaluate("""
            () => {
                const videoElement = document.querySelector('video');
                const playerKeywords = ['player', 'video', 'media'];
                const bodyText = document.body.innerHTML.toLowerCase();
                return videoElement !== null || playerKeywords.some(keyword => bodyText.includes(keyword));
            }
        """)
    
    # 处理视频播放
    async def _handle_video_playback(self):
        """
        如果页面中检测到视频元素，则自动播放视频并等待播放结束。
        """
        try:
            # 注入监听器及状态标记（使用更独特的变量名避免冲突），并判断 readyState
            await self.page.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    if (video) {
                        window.__autoAnalyzer_videoEnded = false;
                        video.addEventListener('ended', () => {
                            window.__autoAnalyzer_videoEnded = true;
                        });
                        video.muted = true;  // 静音防止自动播放被阻止
                        if (video.readyState >= 2) {
                            video.play();
                        }
                    }
                }
            """)
            print(f"⏳ [{self.platform}] 视频播放中(最长10s)，等待播放完成...")
            # 最多等待10秒，超过时间则停止等待
            for i in range(10):
                ended = await self.page.evaluate("window.__autoAnalyzer_videoEnded")
                if ended:
                    print(f"✅ [{self.platform}] 视频播放结束")
                    break
                await asyncio.sleep(1)
            else:
                print(f"⚠️ [{self.platform}] 视频播放超时未结束，停止等待")
        except Exception as e:
            log_error(f"❌ [{self.platform}] 视频播放处理失败: {e}")
            print(f"❌ [{self.platform}] 视频播放处理失败: {e}")

    # 收集页面加载过程中所有资源信息
    async def collect(self):
        """
        收集页面加载过程中所有资源信息。
        如果检测到视频页面，则自动播放视频并等待播放结束。
        """
        try:
            # 创建 DevTools 协议连接
            client = await self.page.context.new_cdp_session(self.page)
            await client.send("Network.enable")

            # 监听所有请求,得到启动器链
            client.on("Network.requestWillBeSent", lambda e: asyncio.create_task(self._handle_request(e)))
            
            # 监听所有响应，使用 lambda 包裹异步函数，得到响应的所有URL
            self.page.on("response", lambda res: asyncio.create_task(self._handle_response(res)))

            print(f"🔗 [{self.platform}] 正在打开页面: {self.url}")
            await self.page.goto(self.url, wait_until="load", timeout=60000)

            print(f"🌐 [{self.platform}] 页面加载完成，开始检查资源...")
            print(f"🔍 [{self.platform}] 检查是否为视频页面...")
            is_video_page = await self._is_video_page()
            if is_video_page:
                print(f"🎬 [{self.platform}] 检测到视频元素，启动自动播放监控...")
                await self._handle_video_playback()
            else:
                print(f"📄 [{self.platform}] 未检测到视频元素，普通网页模式，等待加载资源...")
                await asyncio.sleep(10)  # 等待其他资源加载完毕

        except Exception as e:
            log_error(f"❌ [{self.platform}] 页面资源收集失败: {e}")
            print(f"❌ [{self.platform}] 页面资源收集失败: {e}")
        finally:
            try:
                await self.page.wait_for_timeout(60000) # 等待60秒，确保所有请求完成
            except Exception as e:
                log_error(f"⚠️ [{self.platform}] 页面关闭时发生错误: {e}")
                print(f"⚠️ [{self.platform}] 页面关闭时发生错误: {e}")

    async def get_parsed_responses_data(self):
        """
        提取页面加载过程中捕获的资源信息。

        :return: 包含资源详细信息的列表
        """
        data = []
        print("📊 收集资源数据...")
        for res_data in self.responses:
            res = res_data["response"]
            try:
                req = res.request
                headers = res.headers
                content_type = headers.get("content-type", "未知")
                length = headers.get("content-length", None)
                if length is None:
                    try:
                        body = await res.body()
                        length = len(body)
                    except Exception:
                        length = "未知"
                data.append({
                    "url": res.url,
                    "status": res.status,
                    "type": req.resource_type,
                    "content_type": content_type,
                    "size": length
                    # "headers": dict(headers)  # 保留完整请求头用于调试（调试时使用）
                })
            except Exception as e:
                log_error(f"[错误] {res.url} => {e}")
                print(f"[错误] {res.url} => {e}")
                continue

        return data
    
    async def get_initiator_map(self):
        """
        获取请求的启动器链信息。

        :return: 启动器链信息的字典
        """
        return self.initiator_map

class ResourceInspector:
    """
    对采集到的资源数据做补充分析：
      - 判断 URL 是否允许访问（通过 HEAD 请求判断，不行则降级为 GET）
      - 解析 URL 域名归属，并根据返回所属厂商
      - 根据资源类型推断其在页面中的功能及是否可能阻塞加载
    """

    resource_function_mapping = {
        "document": ("HTML 文档，页面加载的核心资源，定义了页面的结构和内容，是其他资源加载的入口点", "通常是阻塞型资源"),
        "script": ("JavaScript 文件，用于实现页面的动态交互和逻辑功能", "可能会阻塞页面渲染，尤其是同步加载的脚本"),
        "stylesheet": ("CSS 文件，用于定义页面的样式和布局，是渲染页面的重要资源", "通常是渲染阻塞型资源"),
        "image": ("图片资源，用于丰富页面的视觉效果", "通常是非阻塞型资源，但可能影响页面加载性能"),
        "font": ("字体文件，用于定义页面的文字样式", "通常是非阻塞型资源，可能会延迟文字的显示，影响用户体验。"),
        "xhr": ("XHR 请求，用于异步加载数据", "通常不会阻塞页面加载，但可能影响页面的动态内容更新。"),
        "fetch": ("Fetch API 请求，用于现代化的异步数据加载", "通常不会阻塞页面加载，适合处理复杂的网络请求。"),
        "media": ("媒体文件，包括视频和音频资源", "通常不会阻塞页面加载，但可能占用较多带宽。"),
        "ping": ("Ping 请求，用于发送轻量级的网络请求，通常用于点击追踪或统计分析", "异步发送，不阻塞页面。"),
        "other": ("其他资源", "未明确分类的资源，具体功能需视具体情况而定，可能对页面加载有不同程度的影响。")
    }

    def __init__(self, resource_data, initiator_map):
        """
        初始化 ResourceInspector 类。

        :param resource_data: 页面加载过程中采集到的资源数据
        """
        self.resource_data = resource_data
        self.initiator_map = initiator_map  # 用于存储请求启动链

    def get_blocking_use_map(self, url) -> bool:
        """
        判断某个 URL 是否可能阻塞页面加载。

        :param url: 资源的 URL
        :return: 布尔值，表示是否可能阻塞页面加载
        """
        for key, value in self.initiator_map.items():
            if url == value.get("url", None):
                return True
            
            if value.get("stack", None):
                for callFramesitem in value["stack"].get("callFrames", []):
                    if url == callFramesitem.get("url") :
                        return True
            
        return False
        
    def get_vendor(self, url: str) -> dict:
        """
        获取资源的厂商信息，包括 WHOIS 和 IP 信息。

        :param url: 资源的 URL
        :return: 包含厂商信息的字典
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        result = {
            "whois": "Unknown",
            "ipwhois": "Unknown",
            "asn_description": "Unknown"
        }

        try:
            # 使用 whois 查询（阻塞调用，建议使用线程池包装）
            domain_info = whois.whois(domain)
            if (domain_info.registrar):
                result["whois"] = domain_info.registrar or "Unknown"
        except Exception as e:
            log_error(f"[错误] WHOIS 查询失败: {e}")

        try:
            # 使用 DNS 解析并通过 ipwhois 查询
            answers = dns.resolver.resolve(domain, 'A')  # 获取 A 记录
            ip_address = answers[0].address  # 获取第一个 IP 地址
            obj = IPWhois(ip_address)
            ip_result = obj.lookup_rdap()
            entities = ip_result.get("entities", ["Unknown"])
            result["ipwhois"] = entities[0] if entities else "Unknown"
            result["asn_description"] = ip_result.get("asn_description", "Unknown")
        except Exception as e:
            log_error(f"[错误] 获取厂商信息失败: {e}")

        return result

    def analyze_resource_function(self, resource_type: str):
        """
        根据资源类型推断其功能和加载影响。

        :param resource_type: 资源类型
        :return: 功能描述和加载影响的元组
        """
        resource_type = resource_type.lower()
        return self.resource_function_mapping.get(resource_type, self.resource_function_mapping.get("other"))

    async def check_url_accessibility(self, session: aiohttp.ClientSession, url: str) -> bool:
        """
        检查资源的 URL 是否可访问。
        HEAD 请求失败时降级为 GET 请求。

        :param session: 共享的 aiohttp ClientSession
        :param url: 资源的 URL
        :return: 是否可访问的布尔值
        """
        try:
            async with session.head(url, timeout=10) as response:
                if response.status == 405:
                    raise Exception("HEAD 不被允许")
                return response.status < 400
        except Exception:
            try:
                async with session.get(url, timeout=10) as response:
                    return response.status < 400
            except Exception as e:
                log_error(f"[错误] URL 访问检查失败 {url}: {e}")
                return False

    def classify_resource_type(self, url: str) -> str:
        """
        根据 URL 的 path 自动分类资源类型。

        :param url: 资源的 URL
        :return: 分类后的资源类型
        """
        path = urlparse(url).path.lower()  # 提取并转换为小写
        if path.endswith(('.html', '.htm', '/')):
            return "document"
        elif path.endswith(('.js',)):
            return "script"
        elif path.endswith(('.css',)):
            return "stylesheet"
        elif path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp')):
            return "image"
        elif path.endswith(('.woff', '.woff2', '.ttf', '.otf', '.eot')):
            return "font"
        elif path.endswith(('.mp4', '.webm', '.ogg', '.mp3', '.wav')):
            return "media"
        elif "xhr" in path or "api" in path:
            return "xhr"
        elif "fetch" in path:
            return "fetch"
        else:
            return "other"

    async def analyze(self):
        """
        对采集到的资源数据进行分析，补充厂商信息、功能描述等。

        :return: 分析后的资源数据列表
        """
        analysis_results = []
        # 建立一个共享的 aiohttp session 提高效率
        async with aiohttp.ClientSession() as session:
            # 并发执行各项 vendor 查询（阻塞任务使用线程池包装）
            loop = asyncio.get_running_loop()
            for resource in self.resource_data:
                url = resource.get("url")
                resource_type = resource.get("type", None)
                if not resource_type:
                    resource_type = self.classify_resource_type(url)
                # 将阻塞的厂商查询封装进线程池中执行
                vendor = await loop.run_in_executor(None, self.get_vendor, url)
                function_desc, _ = self.analyze_resource_function(resource_type)
                accessible = await self.check_url_accessibility(session, url)
                blocking_comment = self.get_blocking_use_map(url)
                # 记录分析结果
                analysis = {
                    "url": url,
                    "accessible": accessible,
                    "vendor": vendor,
                    "resource_type": resource_type,
                    "content_type": resource.get("content_type"),
                    "function_description": function_desc,
                    "blocking_comment": blocking_comment
                }
                analysis_results.append(analysis)
        return analysis_results

def save_to_json(data, output_path: str, mode="w"):
    """
    将传入的 dict 或 list 数据写入 JSON 文件。

    :param data: 准备写入的 dict 或 list 数据
    :param output_path: 输出 JSON 文件的路径
    :param mode: 文件写入模式，默认为 "w"
    """
    try:
        # 检查数据类型
        if not isinstance(data, (dict, list)):
            raise ValueError("数据类型错误，必须为 dict 或 list")

        # 确保目录存在
        output_path = Path(output_path)  # 转换为 Path 对象
        output_path.parent.mkdir(parents=True, exist_ok=True)  # 递归创建目录

        # 写入 JSON 文件
        with output_path.open(mode, encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

        print(f"JSON 数据成功写入: {output_path}")

    except ValueError as ve:
        log_error(f"数据错误: {ve}")
        print(f"数据错误: {ve}")
    except FileNotFoundError:
        log_error("无法找到指定路径，请检查 output_path 是否正确")
        print("无法找到指定路径，请检查 output_path 是否正确")
    except PermissionError:
        log_error("无权限写入文件，请检查文件权限")
        print("无权限写入文件，请检查文件权限")
    except Exception as e:
        log_error(f"写入 JSON 失败: {e}")
        print(f"写入 JSON 失败: {e}")

async def main(url, platform):
    """
    主函数，负责调用 ResourceAnalyzer 和 ResourceInspector 对页面资源进行分析。

    :param url: 要分析的页面 URL
    :param platform: 平台名称，用于标识当前分析的平台
    :return: 分析后的资源数据
    """
    resource_data = []
    initiator_map = {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, 
                channel="chrome",
                args=[
                    "--start-maximized",  # 最大化窗口
                    "--autoplay-policy=no-user-gesture-required",  # 允许自动播放
                    "--disable-infobars",  # 禁用信息栏
                    "--disable-blink-features=AutomationControlled",  # 反自动化检测
                    "--disable-dev-shm-usage",  # 共享内存优化
                    "--no-sandbox",  # 取消沙盒模式
                    "--enable-gpu",  # 启用 GPU 加速
                    "--disable-extensions",  # 禁用扩展
                ]
            )
            context = await browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"),
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": f"{url}",
                    "Connection": "keep-alive"
                }
            )
            page = await context.new_page()

            analyzer = ResourceAnalyzer(url, page, platform)
            await analyzer.collect()
            resource_data = await analyzer.get_parsed_responses_data()
            initiator_map = await analyzer.get_initiator_map()

            # 逐级关闭页面、上下文和浏览器
            await context.close()
            await browser.close()

    except ConnectionResetError as e:
        log_error(f"⚠️ [警告] 连接重置错误: {e}")
        print(f"⚠️ [警告] 连接重置错误: {e}")
    except Exception as e:
        log_error(f"❌ [错误] 分析失败: {e}")
        print(f"❌ [错误] 分析失败: {e}")

    inspector = ResourceInspector(resource_data, initiator_map)
    analysis_results = await inspector.analyze()
    return analysis_results, initiator_map

def analyze_platform(platform, url):
    """
    分析单个平台的资源并保存结果。

    :param platform: 平台名称
    :param url: 平台对应的 URL
    """
    print(f"🌐 [开始] 正在分析平台: {platform}, URL: {url}")
    outputfile_analyse = f"networkdata/resource_analysis_{platform}.json"
    outputfile_initiator = f"networkdata/initiator_map_{platform}.json"

    try:
        analysis_results, initiator_map = asyncio.run(main(url, platform))
        save_to_json(analysis_results, outputfile_analyse, mode="w")
        save_to_json(initiator_map, outputfile_initiator, mode="w")
        print(f"✅ [完成] 平台 {platform} 的资源分析结果已保存到 {outputfile_analyse}")
        print(f"✅ [完成] 平台 {platform} 的请求启动器链已保存到 {outputfile_initiator}")
    except Exception as e:
        log_error(f"❌ [失败] 平台 {platform} 分析失败: {e}")
        print(f"❌ [失败] 平台 {platform} 分析失败: {e}")


def single():
    """
    单线程分析单个平台的资源。
    """
    platform = "cctv"
    url = "https://sports.cctv.cn/?spm=C90324.PE6LRxWJhH5P.E2XVQsMhlk44.7"
    analyze_platform(platform, url)

def mul():
    platform_url_mapping = {
        "ifeng": "https://v.ifeng.com/c/8iSUQYNA2rt",                                # 凤凰视频某视频界面
        "baisou": "https://v.xiaodutv.com/",                                         # 百搜视频主页
        "thepaper": "https://www.thepaper.cn/channel_26916",                         # 澎湃新闻某视频界面
        "haokan": "https://haokan.baidu.com/v?vid=8018351694391431472",              # 百度好看某视频界面
        "ku6": "https://www.ku6.com/detail/663",                                     # 酷6辟谣专栏
        "cctv": "https://sports.cctv.cn/?spm=C90324.PE6LRxWJhH5P.E2XVQsMhlk44.7",    # 体育频道
        "bilibili": "https://www.bilibili.com/video/BV1x1dcY4EbM",                   # 哔哩哔哩某视频界面
    }

    print("🚀 [启动] 开始多线程分析所有平台...")
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [
            executor.submit(analyze_platform, platform, url)
            for platform, url in platform_url_mapping.items()
        ]
        for future in futures:
            future.result()  # 等待每个线程完成

    print("🔚 [结束] 所有平台分析完成")

if __name__ == "__main__":
    """
    主程序入口，负责多线程并发分析多个平台的资源。
    """

    single()
