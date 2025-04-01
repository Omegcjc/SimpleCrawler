
import json
from pathlib import Path
import pandas as pd
from typing import List, Dict



def json_to_excel_converter(json_dir: str, excel_path: str) -> None:
    """
    将指定目录下的多个JSON文件转换为Excel文件，使用pathlib处理路径
    
    :param json_dir: JSON文件所在目录路径
    :param excel_path: 输出的Excel文件路径
    """
    errors: List[str] = []
    json_dir_path = Path(json_dir)  # 转换为Path对象
    
    try:
        # 1. 验证目录存在性（使用pathlib）
        if not json_dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {json_dir_path}")
        if not json_dir_path.is_dir():
            raise NotADirectoryError(f"路径不是目录: {json_dir_path}")

        # 2. 读取JSON文件
        json_data_list: List[Dict] = []
        for file_path in json_dir_path.iterdir():  # 直接遍历Path对象
            # 跳过非JSON文件（使用suffix属性）
            if file_path.suffix.lower() != '.json':
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, dict):
                            errors.append(f"数据结构错误 [{file_path.name}]: 内容不是字典")
                            continue
                        json_data_list.append(data)
                    except json.JSONDecodeError as e:
                        errors.append(f"JSON解析失败 [{file_path.name}]: {str(e)}")
            except (IOError, PermissionError) as e:
                errors.append(f"文件读取失败 [{file_path.name}]: {str(e)}")

        # 后续代码保持不变...
        if not json_data_list:
            raise ValueError("没有找到有效的JSON数据")

        try:
            df = pd.DataFrame(json_data_list)
            df.to_excel(excel_path, index=False, engine='openpyxl')
        except Exception as e:
            raise RuntimeError(f"数据转换或写入失败: {str(e)}")

    except Exception as e:
        errors.insert(0, f"致命错误: {str(e)}")
        raise
    finally:
        if errors:
            print("\n处理过程中发生以下错误：")
            for error in errors:
                print(f"• {error}")


# 测试生成Excel文件使用
# python -m tools.file_tools

if __name__ == "__main__":
    JSON_DIRECTORY = "data/thepaper/videos/use_id"
    EXCEL_OUTPUT = "excel/thepaper_use_id.xlsx"
    
    try:
        json_to_excel_converter(JSON_DIRECTORY, EXCEL_OUTPUT)
        print(f"\n成功生成Excel文件: {EXCEL_OUTPUT}")
    except Exception as e:
        print(f"\n处理终止: {str(e)}")