from bs4 import BeautifulSoup

from base.base_crawler import BaseCrawler
from base.base_config import VIDEO_INFO_ALL, DownloadTask

from tools.scraper_utils import dynamic_scroll

from config.thepaperConfig import ThepaperCrawlerConfig


from config.config import *
logger = logging.getLogger(__name__)

class ThepaperCrawler(BaseCrawler):

    def _process_search(self, target: str):
        try:
            # 根据target进行搜索
            search_url = self.config.SEARCH_URL.format(target)
            self._pre_page_handle(search_url) # 默认澎湃新闻网增加了自动滑动屏幕的次数 -> 5次

            result_list =  self._process_search_to_list(target)

            video_num = 0
            for idex, result in enumerate(result_list):
                # 处理每个搜索结果
                if video_num >= self.max_video_num:
                    logger.info(f"======[{self.config.PLATFORM}]已达到最大视频处理数量，停止添加======")
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


            # if self.mulithreaded_download:
            #         self.download_manager.finish_adding_tasks()
            #         logger.info(f"======[{self.config.PLATFORM}]已达到最大视频处理数量，停止添加======")
            #         self.download_manager.wait_for_all_and_stop()
        except Exception as e:
            logger.error(f"发生错误：{e}")
            raise            
        
    def _process_search_to_list(self, target):

        result_list = []
        list_items = self.page.query_selector_all('[class*="index_searchresult"] ul li')  # 模糊匹配包含关键字的class
        for li in list_items:
            try:
                # 提取链接元素
                card = li.query_selector('.mdCard')
                if not card:
                    continue
                
                a_tag = card.query_selector('a[href]')
                if not a_tag:
                    continue

                # 处理相对路径
                raw_href = a_tag.get_attribute('href').strip()
                ID = raw_href.split("_")[2]
                
                # 提取标题文本并清理格式
                h2 = a_tag.query_selector('h2')
                if h2:
                    # 移除所有HTML标签只保留文本
                    title = h2.inner_text().strip()
                    # 合并连续空格和换行符
                    title = ' '.join(title.split())
                else:
                    title = "无标题"

                result_list.append({
                    'ID': ID,
                    'title': title
                })
            except Exception as e:
                print(f"解析元素时出错: {str(e)}")
                continue

        self._save_videolist(result_list, target)

        logger.info(f"搜索关键词为：{target}, 总共得到{len(result_list)}条数据")
        return result_list
    
    def _process_video(self, target: str):
        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode = 'all')       #重置所有内容

        # 固定内容赋值
        video_info.platform = self.config.PLATFORM              # [视频信息] 平台 - ifengConfig          
        video_info.base_url = self.config.BASE_URL              # [视频信息] base_url - ifengConfig
        video_info.id = target                                  # [视频信息] id = target

        try:
            # 初始化页面
            video_url = self.config.VIDEO_URL.format(target)
            self._pre_page_handle(video_url,scroll_times=2)  # 确保包含页面加载等待逻辑

            all_data = self.page.evaluate('''() => {
                return window.__NEXT_DATA__ || {};
            }''')

            if not all_data:
                logger.error("未找到页面数据")
                raise

            ContentDetail = all_data["props"]["pageProps"]["detailData"]["contentDetail"]

            videos = ContentDetail["videos"] if "videos" in ContentDetail else {}

            if not videos:
                return False
            
            ID = ContentDetail["contId"] if "contId" in ContentDetail else target
            title = ContentDetail["name"] if "name" in ContentDetail else "无标题"
            desc = ContentDetail["summary"] if "summary" in ContentDetail else None
            keywords = ContentDetail["trackKeyword"] if "trackKeyword" in ContentDetail else None
            author = ContentDetail["author"] if "author" in ContentDetail else None
            time = ContentDetail["pubTime"] if "pubTime" in ContentDetail else None
            channel = ContentDetail["tags"] if "tags" in ContentDetail else None

            video_src = videos["url"] if "url" in videos else None
            duration = videos["duration"] if "duration" in videos else None

            html_content = self.page.content()
            
            # 获取点赞数
            video_data_parts = self._parse_video_data(html_content)


            if not video_src:
                raise ValueError("视频源地址为空")
            
            # 保存信息
            video_info.video_url = video_url                # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src             # [视频信息] download_url - 视频源地址
            video_info.likes = video_data_parts['likes']    # [视频信息] likes - 支持数 / 点赞数 / 热度值
            video_info.title = title                        # [视频信息] title - 视频标题
            video_info.desc = desc                          # [视频信息] brief - 简介，可以为None
            video_info.author = author                      # [视频信息] source - 可能为作者，可能为来源地
            video_info.duration = duration                  # [视频信息] duration - 视频时长
            video_info.publish_date = time                  # [视频信息] createdate - 发布时间
            video_info.channel = channel                   # [视频信息] keywords

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

        return True

    def _parse_video_data(self, html_content):
        '''获取点赞数'''
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 获取点赞数
            likes_tag = soup.find("div", lambda x: x and "praiseNum" in x)
            likes = likes_tag.text.strip() if likes_tag else "0"

            return {
                "likes":likes
            }


        except Exception as e:
            logger.error(f"解析 HTML 失败: {e}")
            return None



# 测试实例
# 命令行输入：python -m core.thepaper_crawler

if __name__ == "__main__":

    config = ThepaperCrawlerConfig()
    def test_search():
        """正常搜索测试"""
        try:
            crawler = ThepaperCrawler(headless = True, config=config)
            crawler.crawl("search", "特朗普")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    # print("--- 执行正常搜索测试 ---")
    test_search()

    def crawler_use_id():

        all_id=[ 
            "30542576",
            "30542843",
            "30542716",
            "30542474",
            "30542167",
            "30541342",
            "30535765",
            "30541124",
            "30535916",
            "30533800"
        ]# 总共十个视频

        for index, item in enumerate(all_id):
            try:
                print(f"第{index + 1}个video:{item}开始处理")
                crawler = ThepaperCrawler(headless=True, config = config)
                crawler.crawl("video", item)
                print(f"第{index + 1}个video:{item}成功完成")
            except Exception as e:
                print(f"第{index + 1}个video:{item}处理异常")
                pass

    # crawler_use_id()