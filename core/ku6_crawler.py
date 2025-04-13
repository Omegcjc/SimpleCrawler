from bs4 import BeautifulSoup

from base.base_crawler import BaseCrawler
from base.base_config import VIDEO_INFO_ALL, DownloadTask

from tools.scraper_utils import dynamic_scroll

from config.ku6Config import Ku6CrawlerConfig

# 日志系统
from config.config import *
logger = logging.getLogger(__name__)

class Ku6Crawler(BaseCrawler):

    def _process_search(self, target: str):
        logger.info("ku6网站无法搜索，请直接输入视频ID")
        return
        
    def _process_video(self, target: str):

        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode = 'all')       #重置所有内容

        # 固定内容赋值
        video_info.platform = self.config.PLATFORM              # [视频信息] 平台 - ku6Config          
        video_info.base_url = self.config.BASE_URL              # [视频信息] base_url - ku6Config
        video_info.id = target                                  # [视频信息] id = target

        try:
            # 初始化页面
            video_url = self.config.VIDEO_URL.format(target)
            self._pre_page_handle(video_url)  # 确保包含页面加载等待逻辑

            # 得到title, channel, video_url
            html_content = self.page.content()
            video_data_parts = self._parse_video_data(html_content)

            video_src = video_data_parts['video_url']
            if not video_src:
                logger.error("视频源地址为空")
                raise

            video_info.video_url = video_url                    # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src                 # [视频信息] download_url - 视频下载地址
            video_info.title = video_data_parts["title"]        # [视频信息] title - 视频标题
            video_info.channel = video_data_parts['channel']    # [视频信息] keywords

            self._save_videoinfo(video_info.dict_info_all(), target)

            # 视频下载
            if self.mulithreaded_download:
                task = DownloadTask(
                    url=video_src,
                    save_dir=self.config.OUTPUT_VIDEOMP4_DIR,
                    filename=self.config.OUTPUT_VIDEOMP4_FILENAME.format(target),
                    referer=self.config.BASE_URL
                )

                self.download_manager.add_task(task)
            else:
                self._download_video(target, video_src)

        except Exception as e:
            logger.exception(f"视频处理异常:{e}")
            raise 

    def _parse_video_data(self, html_content):
        """解析 HTML 提取标题、点赞数、播放量等"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # 获取title
            title_tag = soup.find("title")
            title  = title_tag.text.strip() if title_tag else "无标题"

            # 获取channel
            channel_tag = soup.find('a', class_='li-on')
            channel = channel_tag.get_text() if channel_tag else "未知频道"

            # 获取视频链接
            video_tag = soup.find('video', class_='vjs-tech')
            video_src = video_tag['src'] if video_tag else None

            # 输出提取的信息
            video_data = {
                "title":title,
                "channel":channel,
                "video_url":video_src
            }

            logger.info(f"视频信息提取成功")
            return video_data

        except Exception as e:
            logger.error(f"解析 HTML 失败: {e}")
            return None


# 该文件有一个旧版本备份，路径为ku6_crawler_v1.0.py

# 测试实例
# ku6 网没有search功能，因此必须提供视频ID
# ku6 视频网网速较慢，视频下载需要等待

# 命令行输入：python -m core.ku6_crawler

if __name__ == "__main__":

    config = Ku6CrawlerConfig()

    id_list = [
        "QdRTpiXkNC6iPrVnhaN5_tCg5UI.",
        "ni0ugYAYIldNml76-_y8x-W8Hjk",
        "SxLQmoafMS1x2y59w87Ugm58nOg.",
        "cqBR04avXAz8zshJcT20OeXib_0."
    ]

    def test_search():
        """正常测试"""
        try:
            crawler = Ku6Crawler(config = config, mulithreaded_download=True)
            for video_id in id_list:
                crawler.crawl("video", video_id)

            crawler.download_manager.finish_adding_tasks()
            crawler.download_manager.wait_for_all_and_stop()
            print("所有视频下载完成")
            print("测试成功完成")
            return True
        except Exception as e:
            print(f"测试失败: {str(e)}")
            return False
        


    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()




