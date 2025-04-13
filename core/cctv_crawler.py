import requests
import re
from lxml import etree
import json
from multiprocessing import Pool, Queue, Lock
import multiprocessing
import os
import logging

from tools.screen_display import ScreenDisplay
from base.base_contentcrawler import ContentCrawler

from tools.file_tools import save_to_json
from base.base_config import VIDEO_INFO_ALL

class CCTV(ContentCrawler):
    def __init__(self, via='cctv'):
        super().__init__();
        self.platform = 'cctv'
        self.via = via
        self.url = 'https://v.cctv.cn/'
        self.headers.update({'Referer': 'https://v.cctv.cn/'})

    def _get_like(self, video_id=None, www_url=None, queue_jindu=None, lock=None):
        if video_id is None:
            video_id = www_url.split('/')[6].split('.shtml')[0]
        like_url = 'https://common.itv.cntv.cn/praise/batchGet?type=other&id[]='
        like_ori = self.get_content(url=like_url + video_id)
        if like_ori['engine'] == 'selenium':
            like_ori = etree.HTML(like_ori['content']).xpath('//body/text()')[0]
        else:
            like_ori = like_ori['content']
        like_num = json.loads(like_ori)['count']
        with lock:
            display = queue_jindu.get()
            display.progress('正在获取点赞数')
            queue_jindu.put(display)
        return like_num
    
    @ContentCrawler.mode_wrapper('search_list')
    @ContentCrawler.search_key_wrapper
    def search_list(self, keyword, number):
        global len
        accumulate = 0
        page_size = 20; page_number = 1
        videos = []
        multiprocessing_result = []
        pool = Pool(10)
        self.display = ScreenDisplay()
        self.display.progress('正在爬取视频列表', total=(number / page_size + (number % page_size != 0)), fixed=True)
        while accumulate < number:
            request_number = page_size if number - accumulate > page_size else number - accumulate
            url = f'https://media.app.cctv.cn/vapi/video/vplist.do?chid=EPGC1525679284945000,EPGC1716307200000000&title={keyword}&p={page_number}&n={request_number}&cb=t'
            logging.info(f'Search URL: {url}')
            result = pool.apply_async(self.get_content, args=(url,))
            multiprocessing_result.append(result)
            accumulate += request_number
            page_number += 1
            self.display.progress('正在爬取视频列表')
        self.display.progress('正在爬取视频列表', ok=True)
        pool.close()
        pool.join()
        accumulate = 0
        self.display.progress('正在整理数据', total=len(multiprocessing_result), fixed=True)
        for r in multiprocessing_result:
            result = r.get()
            if result['engine'] == 'selenium':
                result = etree.HTML(result['content']).xpath('//pre[1]/text()')[0]
            else:
                result = result['content']
            result = re.match(r'([^\(]*\()(\{.*)\)$', result).group(2)
            logging.info(f'Search Result: {result}')
            json_form = json.loads(result)
            for index, item in enumerate(json_form['data']):
                logging.debug(f'{index}')
                # 获取其中的点赞数
                wwwURL = item['wwwUrl']
                videoID = wwwURL.split('/')[6].split('.shtml')[0]
                videos.append({
                    'index': accumulate,
                    'title': item['title'],
                    'desc': item['vbrief'],
                    'video_ID': videoID,
                    'guid': item['guid'],
                    'author': item['mediaName'],
                    'publish_date': {
                        'timestamp': item['pubTime'] / 1000,
                        'granularity': 'microsecond'
                    },
                    'video_url': wwwURL,
                    'keywords': item['keywords'].split(','),
                    'channel': item['cateName'],
                    'duration': item['vduration'],
                    'views': None,
                    'platform': self.platform,
                    'via': self.via,
                    'search_key': self.search_key,
                })
                accumulate += 1
            if not json_form['data']:
                break
            self.display.progress('正在整理数据')
        self.display.progress('正在整理数据', ok=True)
        logging.info(f'{videos}')
        multiprocessing_result = []
        pool = Pool(16)
        queue_jindu = multiprocessing.Manager().Queue()
        lock = multiprocessing.Manager().Lock()
        self.display.progress('正在获取点赞数', total=len(videos), fixed=True)
        queue_jindu.put(self.display)
        for index, video in enumerate(videos):
            logging.debug(f"{index}: {video['video_url']}")
            result = pool.apply_async(self._get_like, (video['video_ID'], video['video_url'], queue_jindu, lock))
            multiprocessing_result.append(result)
        pool.close()
        pool.join()
        self.display = queue_jindu.get()
        self.display.progress('正在获取点赞数', ok=True)
        for index, r in enumerate(multiprocessing_result):
            result = r.get()
            videos[index].update({'like': result})
        for video in videos:
            video.update(self.capture_one_video(title=video['title'], wwwUrl=video['video_url'], guid=video['guid'], mode='list'))
        return videos
    @ContentCrawler.mode_wrapper('search_id')
    @ContentCrawler.search_key_wrapper
    def search_video_id(self, video_id):
        url = 'https://v.cctv.cn/20' + video_id[-6:-4] + '/' + video_id[-4:-2] + '/' + video_id[-2:] + '/' + video_id + '.shtml'
        title = self.get_content(url=url, xpath='/html/head/title')['content']
        logging.info(f'{title}')
        # 下载视频
        result = self.capture_one_video(title=None, wwwUrl=url, guid=None, mode='ID')
        # 通过搜索获得该视频的详细信息: 搜索页面的信息比详情页面更详细
        # 逐渐增大关键词模糊度, 并增大搜索列表的个数
        global len
        num = 3; length = len(title)
        while length > 0:
            probable_list = self.search_list(title[0 : length + 1], num)
            for item in probable_list:
                # print(title[0 : length + 1], item['title'])
                if item['video_ID'] == video_id:
                    result.update(item)
                    result['mode'] = self.mode
                    result['search_key'] = self.search_key
                    return result
            length = len // 2; num = num * 2
        # 再删掉开头的字词试一下
        while length > 0:
            probable_list = self.search_list(title[-length:], num)
            for item in probable_list:
                # print(title[-length:], item['title'])
                if item['video_ID'] == video_id:
                    result.update(item)
                    result['search_key'] = self.search_key
                    return result
            length = len // 2; num = num * 2
        else:
            return result
    def capture_one_video(self, title=None, wwwUrl=None, guid=None, mode='ID'):
        """
        这个方法用于在已经获得详细信息的情况下下载视频, 而非获取详细信息
        :param title: 视频标题
        :param wwwUrl: 视频 URL, 必须
        :param guid: 视频 guid
        :return:
        """
        self.display.info('正在获取视频地址', fixed=False)
        result = self.get_content_requests(wwwUrl)['content']
        html = None
        if not title or not guid:
            html = etree.HTML(result)
        if not title:
            title = html.xpath('//title/text()')[0]
        if not guid:
            guid = re.findall('guid = "(.*)";', result)[0]
        # 获取 m3u8 文件地址
        response = requests.get('https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid=' + guid)
        json_data = json.loads(response.content.decode())
        hls_url = json_data['hls_url']
        # 获取 main_m3u8
        response = requests.get(hls_url)
        main_m3u8 = response.content.decode()
        # 获取某个分辨率的 m3u8 文件
        # 央视网的 ts 文件只有 480P 的下载后是正常的
        cdn_domain = self.pure_domain(hls_url, slash=False)
        m3u8_list = re.findall(r'\n(.*/([0-9]*)\.m3u8)\n', main_m3u8)
        max_res = 0
        max_res_source = None
        for index, m3u8 in enumerate(m3u8_list):
            if int(m3u8[1]) > max_res:
                max_res = int(m3u8[1])
                max_res_source = m3u8[0]
        url = cdn_domain + max_res_source
        base_url = url.rsplit(sep='/', maxsplit=1)[0] + '/'
        # print(url)
        # print(base_url)
        response = requests.get(url)
        # print(response.content.decode())
        m3u8 = response.content.decode()
        # 下载视频
        period_list = re.findall(r',\n(.*\.ts)\n', m3u8)
        global len
        self.display.progress('正在下载视频', total=len(period_list), fixed=True)
        # !!!!!!!!!!!!!!!!!!!!!!!!! 文件输入输出 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        path_dict_mp4 = self.filename(title, self.mode, 'mp4', 2, self.via, 'cctv')
        path_dict_ts = self.filename(title, self.mode, 'ts', 2, self.via, 'cctv')

        for period in period_list:
            # print(period)
            video_url = base_url + period
            response = requests.get(video_url)
            with open(path_dict_ts['output_path'], 'ab+') as f:
                f.write(response.content)
            self.display.progress('正在下载视频')
        self.display.progress('正在下载视频', ok=True)
        # 防止 ffmpeg 询问覆写的问题
        if os.path.exists(path_dict_mp4['output_path']):
            os.remove(path_dict_mp4['output_path'])
        
        self.convert_ts_to_mp4(path_dict_ts['output_path'])
        # 删除 ts 文件
        if os.path.exists(path_dict_ts['output_path']):
            os.remove(path_dict_ts['output_path'])
        return {
            'file_path': path_dict_mp4['output_path'],
            'path': path_dict_mp4['data_dir'],
            'download_url': hls_url,
            'mode': self.mode,
        }



def res_to_video_info(res):
    video_info = VIDEO_INFO_ALL()
    video_info.refresh_info(mode = "all")

    video_info.platform = res['platform']
    video_info.base_url = "htts://v.cctv.cn/"

    video_info.title = res['title']
    video_info.id = res['video_ID']
    video_info.video_url = res['video_url']
    video_info.download_url = res['download_url']
    video_info.author = res['author']
    video_info.publish_date = res['publish_date']
    video_info.desc = res['desc']
    video_info.channel = res['channel']
    video_info.keywords = res['keywords']
    video_info.duration = res['duration']
    video_info.likes = res['like']

    return video_info.dict_info_all()





def CCTVCrawler(mode: str, target:str, number: int = 10):
    """
    央视网爬虫

    :param mode: 模式, 'search' 或 'video'
    :param target: 搜索关键词或视频ID
    :param number: 搜索模式下的结果数量, 默认为10
    """
    cctv = CCTV()

    mode = mode.lower()
    if mode not in ["search", "video"]:
        raise ValueError(f"无效模式: {mode}，支持模式: 'search'/'video'")
        
    target = target.strip() if isinstance(target, str) else target
    if not target:
        raise ValueError(f"无效target: {target}")
    
    result = []
    output_path_search = "data/cctv/search_list/video_{}_info.json"
    output_path_video = "data/cctv/search_id/video_{}_info.json"

    try:
        if mode == "search":

            output_path = output_path_search
            result = cctv.search_list(target, number)
        elif mode == "video":
            output_path = output_path_video
            if isinstance(target, (list, tuple)):  # 检测是否为列表或元组
                for video_id in target:
                    result.append(cctv.search_video_id(video_id.strip()))
            else:
                result.append(cctv.search_video_id(target))
    except Exception as e:
        logging.error(f"{mode}模式爬取失败: {str(e)}")
        raise

    parsed_result = cctv.output(result)

    for item in parsed_result:
        if mode == "search":
            output_path = "data/cctv/search_list/video_{}_info.json".format(item['video_ID'])
        elif mode == "video":
            output_path = "data/cctv/search_id/video_{}_info.json".format(item['video_ID'])

        video_info = res_to_video_info(item)
        save_to_json(video_info, output_path)





if __name__ == '__main__':
    # 测试代码
    CCTVCrawler('search', '朱广权', 10)
    # CCTVCrawler('video', 'C10000500000000000000')








































































