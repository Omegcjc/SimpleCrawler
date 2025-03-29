import subprocess
import random
import time
import shutil
import logging
from pathlib import Path

from config.config import *

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.user_agents = [
            # 主流通用浏览器 User-Agent
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
        ]
        self.min_wait = 2  # 最小随机等待时间（秒）
        self.max_wait = 8  # 最大随机等待时间（秒）

    def download_video_stealth(
        self,
        download_url: str,
        save_dir: str,
        filename: str,
        max_retries: int = 3,
        referer: str = None,
        cookies_file: str = None,
        proxy: str = None
    ):
        """隐身模式下载视频，防止被网站识别为爬虫
        
        :param download_url: 视频下载URL
        :param save_dir: 保存目录
        :param filename: 保存文件名
        :param max_retries: 最大重试次数（默认3次）
        :param referer: 伪造Referer头（可选）
        :param cookies_file: Cookies文件路径（可选）
        :param proxy: 代理服务器地址（如 http://1.2.3.4:8080）
        """
        try:
            if not self._is_wget_installed():
                raise EnvironmentError("wget 未安装")

            # 创建保存目录
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            file_path = Path(save_dir) / filename

            # 构建隐身参数
            wget_command = ["wget", "-O", str(file_path)]
            
            # 随机化关键参数
            wget_command += [
                "--random-wait",  # 启用内置随机等待（1-10秒）
                f"--wait={random.randint(self.min_wait, self.max_wait)}",  # 自定义随机区间
                f"--user-agent={random.choice(self.user_agents)}",  # 随机UA
            ]

            # 可选隐身配置
            if referer:
                wget_command.append(f"--referer={referer}")
            if cookies_file:
                wget_command.append(f"--load-cookies={cookies_file}")
            if proxy:
                wget_command.append(f"--proxy={proxy}")
            
            # 添加目标URL
            wget_command.append(download_url)

            # 执行下载（含重试）
            for attempt in range(max_retries + 1):
                try:
                    subprocess.run(
                        wget_command,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    logger.info(f"隐身下载成功: {file_path}")
                    return
                
                except subprocess.CalledProcessError as e:
                    logger.warning(f"尝试 {attempt+1}/{max_retries} 失败，错误: {e.stderr}")
                    if attempt < max_retries:
                        retry_delay = random.uniform(5, 15)
                        logger.info(f"随机等待 {retry_delay:.1f} 秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        raise RuntimeError(f"经过 {max_retries} 次重试仍失败") from e

        except Exception as e:
            logger.exception("隐身下载失败")
            raise

    def _is_wget_installed(self):
        return shutil.which("wget") is not None
