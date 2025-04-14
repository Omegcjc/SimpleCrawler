
from bs4 import BeautifulSoup

from base.base_crawler import BaseCrawler
from base.base_config import VIDEO_INFO_ALL, DownloadTask

from tools.scraper_utils import dynamic_scroll

from config.ifengConfig import IfengCrawlerConfig

# 日志系统
from config.config import *
logger = logging.getLogger(__name__)


class IfengCrawler(BaseCrawler):

    def _process_search(self, target: str):
        try:
            # 根据target进行搜索
            search_url = self.config.SEARCH_URL.format(target)
            self._pre_page_handle(search_url)

            # 转到视频界面，并提取所有视频src,返回List[results]和视频数量
            results, length = self._process_search_to_videolist(target)
            
            done = 0
            for idex, video in enumerate(results):

                if done >= self.max_video_num:
                    logger.info(f"已达到最大视频数量限制：{self.max_video_num}")
                    break
                try:
                    logger.info(f"======第{idex+1}个视频开始处理======")
                    # 访问单个视频对应链接
                    href_link = video['href']
                    self._pre_page_handle(href_link)

                    all_data = self.page.evaluate('''() => {
                        return allData || {};
                    }''')

                    ID = all_data['docData']['base62Id']
                    if ID:
                        self._process_video(ID)
                        done += 1
                        logger.info(f"======第{idex+1}个视频处理完成======")
                    else:
                        logger.error(f"******第{idex+1}个视频处理异常******")
                        continue # 等全部处理完
                except Exception as e:
                    logger.error(f"第{idex+1}个视频处理异常")
                    continue
        except Exception as e:
            logger.error(f"发生错误：{e}")
            raise
      
    def _process_search_to_videolist(self, target: str):
        '''
        self._process_search函数的增加模块,
        主要用于凤凰网搜索视频初步提取和保存
        返回提取内容列表和提取内容数

        results, len(results)
        '''
        try:
            # 等待 "视频" Tab 元素加载, 转到视频搜索结果界面
            video_tab_selector = "span:has-text('视频')"  # 选择器
            self.page.wait_for_selector(video_tab_selector, timeout=10000)  # 等待元素出现
            self.page.click(video_tab_selector)
            dynamic_scroll(self.page, 1)
            #  self.page.wait_for_load_state("networkidle")  # 等待页面加载完成
            if "视频" in self.page.inner_text("div.index_tabBoxInner_kSu3K"):
                logger.info("成功切换到 '视频' 页面")
            
            # 新增提取逻辑
            results = []
            
            # 基于图片结构的精准定位器
            container_selector = "div.news-stream-newsStream-news-item-infor"
            link_selector = f"{container_selector} h2 a[href]"
            
            # 提取所有目标元素
            elements = self.page.query_selector_all(link_selector)
            
            for idx, element in enumerate(elements, 1):
                # 处理特殊编码的href
                raw_href = element.get_attribute("href")
                
                # 智能补全URL
                if raw_href.startswith("//"):
                    full_href = f"https:{raw_href}" if not raw_href.startswith("//") else f"https://{raw_href[2:]}"
                else:
                    logger.error(f"错误url:{raw_href}")
                    continue
                
                # 清理title中的HTML标签
                dirty_title = element.get_attribute("title") or ""
                clean_title = "".join(dirty_title.split("<em>")).replace("</em>", "").strip()
                
                results.append({
                    "href": full_href,  
                    "title": clean_title
                })

            logger.info(f"提取到 {len(results)} 个视频资源 | 示例：{results[:1] if results else '无结果'}")

            self._save_videolist(results, target)

            return results, len(results)
        except Exception as e:
            logger.error(f"发生错误parse_search_addtion:{e}")
            raise
        
    def _process_video(self, target: str):

        video_info = VIDEO_INFO_ALL()
        video_info.refresh_info(mode = 'all')       #重置所有内容

        # 固定内容赋值
        video_info.platform = self.config.PLATFORM      # [视频信息] 平台 - ifengConfig          
        video_info.base_url = self.config.BASE_URL      # [视频信息] base_url - ifengConfig
        video_info.id = target                          # [视频信息] id = target

        try:
            # 初始化页面
            video_url = self.config.VIDEO_URL.format(target)
            self._pre_page_handle(video_url)  # 确保包含页面加载等待逻辑

            all_data = self.page.evaluate('''() => {
                return allData || {};
            }''')

            if not all_data:
                logger.error("未找到页面数据")
                raise

            docData = all_data['docData'] if "docData" in all_data else {}
            title = docData['title'] if 'title' in docData else "无标题"
            time = docData['newsTime'] if 'newsTime' in docData else None
            video_src = docData['videoPlayUrl'] if 'videoPlayUrl' in docData else None
            author = docData['subscribe']['catename'] if 'subscribe' in docData and 'catename' in docData['subscribe'] else None
            desc = docData['summary'] if 'summary' in docData else None
            duration = docData['duration'] if "duration" in docData else None
            keywords = docData['keywords'] if 'keywords' in docData else None

            # 得到播放量和点赞量
            html_content = self.page.content()
            video_data_parts = self._parse_video_data(html_content)

            video_src = docData['videoPlayUrl']
            if not video_src:
                raise ValueError("视频源地址为空")

            # 保存信息
            video_info.video_url = video_url                # [视频信息] video_url - 直达视频的URL
            video_info.download_url = video_src             # [视频信息] download_url - 视频源地址
            video_info.views = video_data_parts['views']    # [视频信息] views - 播放量
            video_info.likes = video_data_parts['likes']    # [视频信息] likes - 支持数 / 点赞数 / 热度值
            video_info.title = title                        # [视频信息] title - 视频标题
            video_info.desc = desc                          # [视频信息] brief - 简介，可以为None
            video_info.author = author                      # [视频信息] source - 可能为作者，可能为来源地
            video_info.duration = duration                  # [视频信息] duration - 视频时长
            video_info.publish_date = time                  # [视频信息] createdate - 发布时间
            video_info.channel = keywords                   # [视频信息] keywords


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
            # 获取点赞数
            support_count_tag = soup.find("em", id="js_supportCount")
            support_count = support_count_tag.text.strip() if support_count_tag else "0"

            # 获取播放量
            info_tag = soup.find("div", class_=lambda x: x and "index_info" in x)
            if info_tag:
                play_count_tag = info_tag.find('span', class_=lambda x: x and "index_playNum" in x)
                play_count = play_count_tag.text.strip() if play_count_tag else "0"


            # 输出提取的信息
            video_data = {
                "likes": support_count,
                "views": play_count
            }

            logger.info(f"视频信息提取成功")
            return video_data

        except Exception as e:
            logger.error(f"解析 HTML 失败: {e}")
            return None


# 该文件有一个旧版本备份，路径为beifen_ifeng_1.py

# 测试实例
# 命令行输入：python -m core.ifeng_crawler

if __name__ == "__main__":

    config = IfengCrawlerConfig()

    def test_search():
        """正常搜索测试"""
        try:
            crawler = IfengCrawler(config = config)
            crawler.crawl("search", "中美关系")
            print("搜索测试成功完成")
            return True
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            return False

    # 执行测试
    # print("--- 执行正常搜索测试 ---")
    # test_search()

    def crawler_use_id():

        all_id=[ 
            "8iC8PH3pM4d",
            "8iC32aHkMVP",
            "8iC7JbNCxZC",
            "8iBsZ4LMqnS",
            "8iC86qpOj6m",
            "8iAqrCitWbg",
            "8gK0Kp4KVib",
            "8cNu9unfjsx",
            "7sp2PHGgGWm",
            "8bSMzMa5GPN"
        ]# 总共十个视频

        for index, item in enumerate(all_id):
            try:
                print(f"第{index + 1}个video:{item}开始处理")
                crawler = IfengCrawler(headless=True, config = config)
                crawler.crawl("video", item)
                print(f"第{index + 1}个video:{item}成功完成")
                break
            except Exception as e:
                print(f"第{index + 1}个video:{item}处理异常{e}")
                break
                pass
    test_search()



    


