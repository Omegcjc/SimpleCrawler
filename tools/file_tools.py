import json
import logging
from pathlib import Path

# 配置日志
from config.config import *

logger = logging.getLogger(__name__)

def save_to_json(data, output_path: str, mode = "w"):
    """
    将传入的 dict 或 list 数据写入 JSON 文件。

    :param data: 准备写入的 dict 或 list 数据
    :param output_path: 输出 JSON 文件的路径
    """
    try:
        # 检查数据类型
        if not isinstance(data, (dict, list)):
            raise ValueError("数据类型错误，必须为 dict 或 list")

        # 确保目录存在
        output_path = Path(output_path)  # 转换为 Path 对象
        output_path.parent.mkdir(parents=True, exist_ok=True)  # 递归创建目录

        # 写入 JSON 文件
        with output_path.open(mode, encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

        logger.info(f"JSON 数据成功写入: {output_path}")

    except ValueError as ve:
        logger.error(f"数据错误: {ve}")
    except FileNotFoundError:
        logger.error("无法找到指定路径，请检查 output_path 是否正确")
    except PermissionError:
        logger.error("无权限写入文件，请检查文件权限")
    except Exception as e:
        logger.error(f"写入 JSON 失败: {e}")

def debug_help(debug:bool):
    if debug:
        print("=========[DEBUG MODE] 进入调试模式，输入 'exit' 退出。=========")
        while True:
            text = input('输入exit退出整个程序:').strip()
            text = text.lower()
            if text == "exit":
                exit(0)
    else:
        pass