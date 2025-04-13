
from bs4 import BeautifulSoup

from base.base_crawler import BaseCrawler
from base.base_config import VIDEO_INFO_ALL, DownloadTask

from tools.scraper_utils import dynamic_scroll

from config.haokanConfig import HaokanCrawlerConfig

# 日志系统
from config.config import *
logger = logging.getLogger(__name__)


class HaokanCrawler(BaseCrawler):

    def _process_search(self, target: str):
        """处理搜索流程"""
        try:
            search_url = self.config.SEARCH_URL.format(target)
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
                    if is_video:
                        logger.info(f"======第{idex+1}个是视频，信息提取完成======")
                        video_num += 1
                    else:
                        logger.info(f"======第{idex+1}个不是视频，信息提取终止======")
                except Exception as e:
                    logger.error(f"======[{self.config.PLATFORM}]第{idex+1}个视频/新闻处理异常======")
                    continue
            # 
            # if self.mulithreaded_download:
            #     self.download_manager.finish_adding_tasks()
            #     logger.info(f"======[{self.config.PLATFORM}]已达到最大视频处理数量，停止添加======")
            #     self.download_manager.wait_for_all_and_stop()

            
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

            self._save_videolist(result_list, target)

            logger.info(f"搜索关键词为：{target}, 总共得到{len(result_list)}条数据")
            return result_list
            
        except Exception as e:
            logger.error(f"处理搜索结果列表时出错: {str(e)}")
            raise
     
    def _process_video(self, target: str):
        """处理视频详情页"""
        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode='all')

        video_info.platform = self.config.PLATFORM
        video_info.base_url = self.config.BASE_URL
        video_info.id = target

        try:
            video_url = self.config.VIDEO_URL.format(target)
            self._pre_page_handle(video_url)

            html_content = self.page.content()

            # from pathlib import Path
            # debug_file = Path("./debug") / f"haokanvideo_{target}.html"
            # debug_file.parent.mkdir(parents=True, exist_ok=True)
            # with open(debug_file, "w", encoding="utf-8") as f:
            #     f.write(html_content)
                
            soup = BeautifulSoup(html_content, "html.parser")
            
            video_element = soup.find("video")
            if not video_element:
                logger.warning("未找到视频元素,可能不是视频页面")
                return False
                
            video_src = video_element.get("src")
            if not video_src:
                raise ValueError("视频源地址为空")
                
            title_element = soup.find("title")
            title = title_element.text.strip() if title_element else None
            if not title:
                raise ValueError("视频标题为空")
            if title:
                title = title.split(',')[0].strip()
            
            desc_element = soup.find("meta", {"itemprop": "description"})
            desc = desc_element.text.strip() if desc_element else None
            
            author_element = soup.find("a", href=lambda x: x and x.startswith("/author/"))
            author = author_element.text.strip() if author_element else None
            
            time_element = soup.find("div", class_="extrainfo-playnums")
            if time_element:
                publish_time = time_element.find("span", class_="extrainfo-playnums-label").next_sibling.strip()
            else:
                publish_time = None
            
            duration_element = soup.find("span", class_="durationTime")
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

            self._save_videoinfo(video_info.dict_info_all(), target)

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

# 测试实例
# 命令行输入：python -m core.haokan_crawler

if __name__ == "__main__":

    config = HaokanCrawlerConfig()
    def test_search():
        """正常搜索测试"""
        try:
            crawler = HaokanCrawler(config = config, mulithreaded_download=True)
            crawler.crawl("search", "特朗普")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    print("--- 执行正常搜索测试 ---")
    test_search()
