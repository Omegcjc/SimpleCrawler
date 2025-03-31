
import re
import os
from tqdm import tqdm
import time
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config.ku6Config import * # 大写的常量，注意在copy时修改对应常量的值

class VideoSpider:
    def __init__(self, video_id, base_dir, cookies, url, headers, method):
        self.cookies = cookies
        self.video_id = video_id
        self.url = url
        self.headers = headers
        self.base_dir = base_dir
        self.method = method
        os.makedirs(self.base_dir, exist_ok=True)

    def request_page(self):
        '''得到对应网页html代码'''
        try:
            response = requests.get(self.url, headers=self.headers, cookies=self.cookies)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"请求页面失败: {e}")
            return None

    def parse_video_info(self, html):
        '''爬取视频信息'''
        soup = BeautifulSoup(html, 'html.parser')

        title_tag = soup.find("title")
        title  = title_tag.text.strip() if title_tag else "无标题"

        # title_match = re.search(r"title'\).text\(\"([^\"]*)\"\);", html)
        # if not title_match:
        #     print("未找到视频标题")
        #     return None
        # title = self.sanitize_filename(title_match.group(1))

        
        channel_tag = soup.find('a', class_='li-on')
        channel = channel_tag.get_text() if channel_tag else "未知频道"

        video_url_match = re.search(
            r"this.src\({type: \"video/mp4\", src: \"([^\"]*)\"", html
        )
        if not video_url_match:
            print("未找到视频URL")
            return None

        return {
            'title': title,
            'channel': channel,
            'video_url': video_url_match.group(1),
            'filename': f"{title}.mp4"
        }

    def original_download(self, video_url, filename):
        file_path = os.path.join(self.base_dir, filename)
        try:
            with requests.get(video_url, headers=self.headers, stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('Content-Length', 0))
                
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as progress_bar:
                    start_time = time.time()
                    downloaded_size = 0
                    
                    with open(file_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=1024*1024):
                            if chunk:
                                file.write(chunk)
                                downloaded_size += len(chunk)
                                progress_bar.update(len(chunk))
                                elapsed_time = time.time() - start_time
                                if elapsed_time > 0:
                                    speed = downloaded_size / elapsed_time
                                    progress_bar.set_postfix(speed=f"{speed/1024:.2f}KB/s")
            print(f"\n视频已成功下载到：{file_path}")
            return True
        except Exception as e:
            print(f"下载失败: {e}")
            return False

    def download_video(self, video_url, filename, method):
        if method == 'chunked':
            downloader = ChunkedDownloader(video_url, filename, self.base_dir, self.headers)
            return downloader.download()
        elif method == 'single':
            return self.original_download(video_url, filename)
        else:  # auto
            downloader = ChunkedDownloader(video_url, filename, self.base_dir, self.headers)
            total_size, supports_range = downloader.check_support_range()
            if supports_range and total_size > 0:
                return downloader.download()
            else:
                return self.original_download(video_url, filename)

    def sanitize_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', '', filename).strip()
    
    def crawel(self):
        html = self.request_page()
        if not html:
            return

        video_info = self.parse_video_info(html)
        if not video_info:
            return

        print(f"频道: {video_info['channel']}")
        print(f"标题: {video_info['title']}")
        print(f"播放量: ku6.com不提供播放量")
        print(f"点赞: ku6.com不提供点赞")
        print(f"简介: ku6.com不提供简介")
        print(f"搜索: ku6.com不提供搜索功能")

    def download(self):
        html = self.request_page()
        video_info = self.parse_video_info(html)
        print(f"开始下载: {video_info['video_url']}")
        if self.download_video(video_info['video_url'], video_info['filename'],method=self.method):
            print("下载完成")

class ChunkedDownloader:
    def __init__(self, video_url, filename, base_dir, headers):
        self.video_url = video_url
        self.filename = filename
        self.base_dir = base_dir
        self.headers = headers

    def check_support_range(self):
        try:
            response = requests.head(self.video_url, headers=self.headers)
            if response.status_code == 200:
                accept_ranges = response.headers.get('Accept-Ranges', 'none').lower()
                content_length = int(response.headers.get('Content-Length', 0))
                supports = accept_ranges == 'bytes' and content_length > 0
                return content_length, supports
            return 0, False
        except Exception as e:
            print(f"检查分块支持失败: {e}")
            return 0, False

    def split_into_chunks(self, total_size, num_chunks=4):
        chunk_size = total_size // num_chunks
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < num_chunks -1 else total_size -1
            chunks.append((start, end))
        return chunks

    def download_chunk(self, chunk_id, start, end, progress_bar, lock, start_time):
        temp_filename = f"{self.filename}.part{chunk_id}"
        temp_path = os.path.join(self.base_dir, temp_filename)
        headers = self.headers.copy()
        headers['Range'] = f"bytes={start}-{end}"
        try:
            with requests.get(self.video_url, headers=headers, stream=True) as response:
                if response.status_code != 206:
                    raise Exception(f"分块{chunk_id}下载失败，状态码：{response.status_code}")
                for data in response.iter_content(chunk_size=1024*1024):
                    if data:
                        with open(temp_path, 'ab') as f:
                            f.write(data)
                        with lock:
                            progress_bar.update(len(data))
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = progress_bar.n / elapsed
                                progress_bar.set_postfix(speed=f"{speed/1024:.2f}KB/s")
            return True
        except Exception as e:
            print(f"分块{chunk_id}下载失败: {e}")
            return False

    def merge_chunks(self, num_chunks):
        file_path = os.path.join(self.base_dir, self.filename)
        with open(file_path, 'wb') as outfile:
            for i in range(num_chunks):
                temp_path = os.path.join(self.base_dir, f"{self.filename}.part{i}")
                with open(temp_path, 'rb') as infile:
                    outfile.write(infile.read())

    def cleanup_temp_files(self, num_chunks):
        for i in range(num_chunks):
            temp_path = os.path.join(self.base_dir, f"{self.filename}.part{i}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def download(self, num_chunks=4):
        total_size, supports_range = self.check_support_range()
        if not supports_range or total_size == 0:
            print("服务器不支持分块下载")
            return False
        
        chunks = self.split_into_chunks(total_size, num_chunks)
        if not chunks:
            return False
        
        try:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=self.filename) as progress_bar:
                lock = threading.Lock()
                start_time = time.time()
                
                with ThreadPoolExecutor(max_workers=num_chunks) as executor:
                    futures = [executor.submit(
                        self.download_chunk,
                        chunk_id=i,
                        start=start,
                        end=end,
                        progress_bar=progress_bar,
                        lock=lock,
                        start_time=start_time
                    ) for i, (start, end) in enumerate(chunks)]
                    
                    done, not_done = wait(futures)
                    if not all(f.result() for f in futures):
                        print("部分分块下载失败，终止合并")
                        self.cleanup_temp_files(num_chunks)
                        return False
                
                self.merge_chunks(num_chunks)
                self.cleanup_temp_files(num_chunks)
            
            print(f"\n视频已成功下载到: {os.path.join(self.base_dir, self.filename)}")
            return True
        except Exception as e:
            print(f"下载失败: {e}")
            return False

if __name__ == "__main__":
    video_id = "SJE4_Ery2u8sCDUNejSkeqLsMAw"
    url = VIDEO_URL.format("video_id")
    spider = VideoSpider(
        video_id=video_id,
        base_dir="/data/ku6",
        headers = HEADERS,
        cookies = COOKIES,
        url=url,
        method = DOWNLOAD_METHOD  # 'single'单线程, 'chunked'多线程, or 'auto'自动选择下载方式
    )
    spider.crawel()
    spider.download()