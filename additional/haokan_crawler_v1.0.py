import json
import logging
import random
import subprocess
import time
from fake_useragent import UserAgent
from pathlib import Path
from typing import Optional, Dict, List
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """配置和工具类"""
    # 平台基础配置
    PLATFORM = "haokan"
    BASE_URL = "https://www.haokan.baidu.com"
    VIDEO_URL = "https://haokan.baidu.com/v?vid={}"
    SEARCH_URL = "https://haokan.baidu.com/web/search/page?query={}"
    MAX_VIDEO_NUM = 10  # 最多在搜索后爬取的视频数
    
    # 输出路径配置
    OUTPUT_VIDEOLIST_DIR = "./data/haokan/search_video_list"
    OUTPUT_VIDEOLIST_FILENAME = "search_{}.json"
    OUTPUT_VIDEOMP4_DIR = "./data/haokan/videos"
    OUTPUT_VIDEOMP4_FILENAME = "video_{}_src.mp4"
    OUTPUT_VIDEOINFO_DIR = "./data/haokan/videos"
    OUTPUT_VIDEOINFO_FILENAME = "video_{}_info.json"
    
    # 浏览器配置
    STEALTH_JS_PATH = ""

    # 浏览器cookie部分，请添加自己的cookie
    SESSDATA = ""

    @staticmethod
    def get_chromium_args():
        """获取浏览器启动参数"""
        return [
            "--start-maximized",
            "--autoplay-policy=no-user-gesture-required",
            "--disable-infobars",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--enable-gpu",
            "--disable-extensions",
        ]
    
    @staticmethod
    def get_headers(Refer:str):
        """获取请求头"""
        return {
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            "extra_http_headers":{
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": f"{Refer}",
                "Connection": "keep-alive",
                "cookie": Config.SESSDATA
            }
        }

    @staticmethod
    def save_to_json(data, output_path: str, mode = "w"):
        """将传入的 dict 或 list 数据写入 JSON 文件"""
        try:
            if not isinstance(data, (dict, list)):
                raise ValueError("数据类型错误，必须为 dict 或 list")

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open(mode, encoding="utf-8") as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)

            logger.info(f"JSON 数据成功写入: {output_path}")

        except Exception as e:
            logger.error(f"写入 JSON 失败: {e}")
            raise

    @staticmethod
    def dynamic_scroll(page:Page, scroll_times=2):
        """模拟人工滚动"""
        for _ in range(scroll_times):
            page.mouse.wheel(0, random.randint(800, 1200))
            time.sleep(random.uniform(1.2, 2.5))

    @staticmethod
    def close_popups(page:Page, max_attempts=3):
        """弹窗关闭策略"""
        for _ in range(max_attempts):
            if close_btn := page.query_selector('.header-vip-close, .popup-close'):
                close_btn.click(timeout=2000)
                time.sleep(0.8)

class VideoInfo:
    """视频信息类"""
    def __init__(self):
        self.platform = None
        self.base_url = None
        self.title = None
        self.id = None
        self.author = None
        self.video_url = None
        self.download_url = None
        self.publish_date = None
        self.channel = None
        self.duration = None
        self.views = None
        self.desc = None
        self.likes = None
        self.coins = None
        self.favs = None
        self.shares = None
    
    def dict_info_all(self):
        """将对象属性转换为字典"""
        return {
            "platform": self.platform,
            "base_url": self.base_url,
            "title": self.title,
            "id": self.id,
            "author": self.author,
            "duration": self.duration,
            "channel":self.channel,
            "video_url": self.video_url,
            "download_url": self.download_url,
            "publish_date": self.publish_date,
            "views": self.views,
            "desc": self.desc,
            "likes": self.likes,
            "coins": self.coins,
            "favs": self.favs,
            "shares": self.shares
        }
    
    def refresh_info(self, mode):
        """重置所有属性为None"""
        if mode == "all":
            self.platform = None
            self.base_url = None
        
        self.title = None
        self.id = None
        self.author = None
        self.video_url = None
        self.download_url = None
        self.publish_date = None
        self.views = None
        self.desc = None
        self.likes = None
        self.coins = None
        self.favs = None
        self.shares = None
        self.duration = None
        self.channel = None

class BrowserClient:
    """浏览器客户端"""
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.p: Optional[sync_playwright] = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def start_browser(self, base_url: str = None, js_path = None, sessdata:str = None):
        """启动浏览器"""
        try:
            self.p = sync_playwright().start() 
            self.browser = self.p.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=Config.get_chromium_args()
            )
            headers = Config.get_headers(base_url)
            self.context = self.browser.new_context(
                accept_downloads=True,
                user_agent=headers["User-Agent"],
                extra_http_headers=headers["extra_http_headers"]
            )

            if js_path:
                self.context.add_init_script(path=js_path)
            
            if sessdata:
                self.context.add_cookies([{
                    'name': 'SESSDATA',
                    'value': sessdata,
                    'domain': ".baidu.com",
                    'path': "/"
                }])
            
            self.page = self.context.new_page()
        except Exception as e:
            logger.error(f"浏览器启动失败，错误: {str(e)}")
            raise
    
    def end_browser(self):
        """关闭浏览器资源"""
        if self.page is not None:
            self.page.close()
        if self.context is not None:
            self.context.close()
        if self.browser is not None:
            self.browser.close()
        if self.p is not None:
            self.p.stop()

class Crawler:
    """好看网爬虫"""
    def __init__(self, headless: bool = True):
        self.client = BrowserClient(headless=headless)
        self.max_retries = 3
        self.max_video_num = Config.MAX_VIDEO_NUM
        self.page: Page = None
        self.user_agents = UserAgent().random
    
    def crawl(self, mode: str, target: str):
        """统一入口方法"""
        mode = mode.lower()
        if mode not in ["search", "video"]:
            raise ValueError(f"无效模式: {mode}，支持模式: 'search'/'video'")
        
        target = target.strip()
        if not target:
            raise ValueError(f"无效target: {target}，请输入与模式对应的target")
        
        self.client.start_browser(Config.BASE_URL)
        self.page = self.client.page

        try:
            if mode == "search":
                self._process_search(target)
            elif mode == "video":
                self._process_video(target)
            
            self.client.end_browser()
        except Exception as e:
            logger.error(f"{mode}模式爬取失败: {str(e)}")
            self.client.end_browser()
            raise

    def _pre_page_handle(self, url, scroll_times = 5):
        """页面预处理与重试机制"""
        retries = 0
        while retries < self.max_retries:
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(2)
                Config.dynamic_scroll(self.page, scroll_times=scroll_times)
                break
            except TimeoutError:
                logger.warning(f"页面加载超时，第{retries+1}次重试")
                retries += 1
                if retries >= self.max_retries:
                    raise
                self.page.reload()
            except Exception as e:
                logger.error(f"页面处理异常: {str(e)}")
                raise

    def _process_search(self, target: str):
        """处理搜索流程"""
        try:
            search_url = Config.SEARCH_URL.format(target)
            self._pre_page_handle(search_url)

            result_list = self._process_search_to_list(target)

            video_num = 0
            for idex, result in enumerate(result_list):
                if video_num >= self.max_video_num:
                    break
                logger.info(f"======第{idex+1}个视频/新闻开始处理======")
                try:
                    target_ID = result['ID']
                    is_video = self._process_video(target_ID)
                    if not is_video:
                        logger.info(f"======第{idex+1}个不是视频，停止处理======")
                    else:
                        logger.info(f"======第{idex+1}个是视频，处理完成======")
                        video_num += 1
                except Exception as e:
                    logger.error(f"======第{idex+1}个视频/新闻处理异常======")
                    pass
        except Exception as e:
            logger.error(f"发生错误：{e}")
            raise            
        
    def _process_search_to_list(self, target):
        """处理搜索结果为列表"""
        try:
            result_list = []
            list_items = self.page.query_selector_all('.list-container.videolist')
            
            for item in list_items:
                try:
                    href = item.get_attribute('href')
                    if not href:
                        continue
                    
                    vid = href.split('vid=')[-1]
                    title_element = item.query_selector('.list-body strong')
                    title = title_element.inner_text().strip() if title_element else "无标题"
                    title = ' '.join(title.split())

                    result_list.append({
                        'ID': vid,
                        'title': title
                    })
                except Exception as e:
                    logger.error(f"解析视频项时出错: {str(e)}")
                    continue

            file_name = Config.OUTPUT_VIDEOLIST_FILENAME.format(target)
            file_path = Path(Config.OUTPUT_VIDEOLIST_DIR) / file_name
            
            Config.save_to_json(result_list, file_path)
            logger.info(f"搜索关键词为：{target}, 总共得到{len(result_list)}条数据")
            return result_list
            
        except Exception as e:
            logger.error(f"处理搜索结果列表时出错: {str(e)}")
            raise
     
    def _process_video(self, target: str):
        """处理视频详情页"""
        video_info = VideoInfo()
        video_info.refresh_info(mode='all')

        video_info.platform = Config.PLATFORM
        video_info.base_url = Config.BASE_URL
        video_info.id = target

        try:
            video_url = Config.VIDEO_URL.format(target)
            self._pre_page_handle(video_url)

            html_content = self.page.content()
            
            debug_file = Path("./debug") / f"haokanvideo_{target}.html"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            soup = BeautifulSoup(html_content, "html.parser")
            
            video_element = soup.find("video")
            if not video_element:
                logger.info("未找到视频元素,可能不是视频页面")
                return False
                
            video_src = video_element.get("src")
            if not video_src:
                raise ValueError("视频源地址为空")
                
            title_element = soup.find("meta", {"itemprop": "name"})
            title = title_element.text.strip() if title_element else "无标题"
            
            desc_element = soup.find("meta", {"itemprop": "description"})
            desc = desc_element.text.strip() if desc_element else None
            
            author_element = soup.find("div", class_="videoinfo-author-name")
            author = author_element.text.strip() if author_element else None
            
            time_element = soup.find("span", class_="videoinfo-playtime")
            publish_time = time_element.text.strip() if time_element else None
            
            duration_element = soup.find("span", class_="duration")
            duration = duration_element.text.strip() if duration_element else None
            
            keywords_meta = soup.find("meta", {"itemprop": "keywords"})
            channel = keywords_meta["content"].split(',')[0].strip() if keywords_meta else None
            
            video_data = self._parse_video_data(html_content)
            
            video_info.video_url = video_url
            video_info.download_url = video_src
            video_info.title = title
            video_info.desc = desc
            video_info.author = author
            video_info.duration = duration
            video_info.publish_date = publish_time
            video_info.channel = channel
            video_info.likes = video_data['likes']
            video_info.views = video_data['views']

            file_path = Path(Config.OUTPUT_VIDEOINFO_DIR) / Config.OUTPUT_VIDEOINFO_FILENAME.format(target)
            Config.save_to_json(video_info.dict_info_all(), file_path)

            self._download_video(target, video_src)

        except Exception as e:
            logger.exception(f"视频处理异常:{e}")
            raise 

        return True

    def _parse_video_data(self, html_content):
        """从HTML中解析视频数据"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            extrainfo = soup.find("div", class_="extrainfo")
            
            if extrainfo:
                playnums_div = extrainfo.find("div", class_="extrainfo-playnums")
                views = "0"
                if playnums_div:
                    import re
                    views_match = re.search(r'(\d+(?:\.\d+)?)(万)?次播放', playnums_div.text)
                    if views_match:
                        number = float(views_match.group(1))
                        if views_match.group(2) == "万":
                            number = number * 10000
                        views = str(int(number))

                likes_div = extrainfo.find("div", class_="extrainfo-zan")
                likes = "0"
                if likes_div:
                    likes_text = likes_div.text.strip()
                    likes_match = re.search(r'(\d+(?:\.\d+)?)(万)?', likes_text)
                    if likes_match:
                        number = float(likes_match.group(1))
                        if likes_match.group(2) == "万":
                            number = number * 10000
                        likes = str(int(number))

                return {"likes": likes, "views": views}

            return {"likes": "0", "views": "0"}

        except Exception as e:
            logger.error(f"解析视频数据失败: {str(e)}")
            return {"likes": "0", "views": "0"}

    def _download_video(self, target, download_url: str):
        """下载视频"""
        try:
            file_name = Config.OUTPUT_VIDEOMP4_FILENAME.format(target)
            file_dir = Config.OUTPUT_VIDEOMP4_DIR

            wget_command = [
                "wget", "-O", str(Path(file_dir) / file_name),
                "--random-wait",
                f"--wait={random.randint(2, 8)}",
                f"--user-agent={random.choice(self.user_agents)}",
                f"--referer={download_url}",
                download_url
            ]

            Path(file_dir).mkdir(parents=True, exist_ok=True)
            
            for attempt in range(self.max_retries):
                try:
                    subprocess.run(wget_command, check=True, capture_output=True, text=True)
                    logger.info(f"视频 {target} 下载完成！")
                    return
                except subprocess.CalledProcessError as e:
                    logger.warning(f"尝试 {attempt+1}/{self.max_retries} 失败，错误: {e.stderr}")
                    if attempt < self.max_retries - 1:
                        retry_delay = random.uniform(5, 15)
                        logger.info(f"等待 {retry_delay:.1f} 秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        raise RuntimeError(f"经过 {self.max_retries} 次重试仍失败") from e

        except Exception as e:
            logger.exception(f"视频下载异常: {e}")
            raise

if __name__ == "__main__":
    def test_search():
        """正常搜索测试"""
        try:
            crawler = Crawler(headless=True)
            crawler.crawl("search", "中东")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    print("--- 执行正常搜索测试 ---")
    test_search()
