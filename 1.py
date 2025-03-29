import subprocess

# 视频 URL
video_url = "https://video19.ifeng.com/video09/2025/03/28/p7311231387082690679-102-114509.mp4"

# 本地保存路径
save_path = "downloaded_video.mp4"

# 构造 wget 命令
wget_command = ["wget", "-O", save_path, video_url]

# 执行命令
try:
    subprocess.run(wget_command, check=True)
    print(f"视频下载完成！文件保存为：{save_path}")
except subprocess.CalledProcessError as e:
    print(f"下载失败: {e}")
