import threading
import queue
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from tools.video_down_wget import VideoDownloader
from base.base_config import DownloadTask

from config.config import *
logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self, max_workers=4):
        self.downloader = VideoDownloader()
        self.task_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._task_count_lock = threading.Lock()
        self._accepting_tasks = True
        self._pending_tasks = 0

        # 统计信息
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0

        self._scheduler_thread.start()

    def add_task(self, task: DownloadTask):
        if not self._accepting_tasks:
            logger.warning(f"任务被拒绝添加（DownloadManager 已关闭）: {task.filename}")
            return

        with self._task_count_lock:
            self.total_tasks += 1
            self._pending_tasks += 1

        self.task_queue.put(task)
        logger.info(f"新任务加入队列: {task.filename} | 当前总任务: {self.total_tasks}")

    def _scheduler_loop(self):
        while True:
            try:
                task = self.task_queue.get(timeout=0.5)
                self.executor.submit(self._execute_task, task)
            except queue.Empty:
                with self._task_count_lock:
                    if not self._accepting_tasks and self._pending_tasks == 0:
                        break

    def _execute_task(self, task: DownloadTask):
        try:
            logger.info(f"开始下载: {task.filename}")
            self.downloader.download_video_stealth(
                download_url=task.url,
                save_dir=task.save_dir,
                filename=task.filename,
                referer=task.referer,
                cookies_file=task.cookies_file,
                proxy=task.proxy
            )
            with self._task_count_lock:
                self.completed_tasks += 1
            logger.info(f"下载完成: {task.filename}")
        except Exception as e:
            with self._task_count_lock:
                self.failed_tasks += 1
            logger.error(f"下载失败: {task.filename} -> {e}")
        finally:
            with self._task_count_lock:
                self._pending_tasks -= 1
            self.task_queue.task_done()
            self._log_progress()

    def _log_progress(self):
        with self._task_count_lock:
            logger.info(
                f"下载进度: "
                f"{self.completed_tasks}/{self.total_tasks} 完成 | "
                f"{self.failed_tasks} 失败 | "
                f"{self._pending_tasks} 剩余"
            )

    def finish_adding_tasks(self):
        """调用此方法表示“所有任务已添加完毕”，DownloadManager将在任务跑完后关闭"""
        logger.info("所有任务已添加，等待执行完毕...")
        self._accepting_tasks = False

    def wait_for_all_and_stop(self):
        """等待全部任务完成后安全退出线程池"""
        self._scheduler_thread.join()
        self.executor.shutdown(wait=True)
        logger.info("所有任务执行完毕，下载管理器已安全关闭")
        self._log_progress()




