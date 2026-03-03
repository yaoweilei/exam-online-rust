#!/usr/bin/env python3
"""
修复 .json 文件：
1. 将 tab 替换为空格（2个空格缩进）
2. 验证 JSON 格式是否正确
"""

import json
from pathlib import Path


def fix_exam_file(file_path: Path) -> tuple[bool, str]:
    """
    修复单个 .json 文件
    返回: (是否成功, 错误信息或成功信息)
    """
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 先尝试解析 JSON，检查是否有错误
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {e}"
        
        # 重新格式化 JSON（使用2个空格缩进）
        formatted = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted)
        
        # 检查是否有变化
        if content != formatted:
            return True, "已修复格式"
        else:
            return True, "格式正确，无需修改"
            
    except Exception as e:
        return False, f"处理错误: {e}"


def main():
    # 查找所有 .json 文件
    base_dir = Path(__file__).parent.parent / "data" / "paper" / "jlpt"
    
    if not base_dir.exists():
        print(f"目录不存在: {base_dir}")
        return
    
    exam_files = list(base_dir.glob("**/*.json"))
    
    if not exam_files:
        print("未找到 .json 文件")
        return
    
    print(f"找到 {len(exam_files)} 个 .json 文件\n")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    errors = []
    
    for file_path in sorted(exam_files):
        relative_path = file_path.relative_to(base_dir.parent.parent.parent)
        success, message = fix_exam_file(file_path)
        
        if success:
            print(f"✓ {relative_path}: {message}")
            success_count += 1
        else:
            print(f"✗ {relative_path}: {message}")
            errors.append((relative_path, message))
            error_count += 1
    
    print("=" * 60)
    print(f"\n总计: {len(exam_files)} 个文件")
    print(f"  ✓ 成功: {success_count}")
    print(f"  ✗ 失败: {error_count}")
    
    if errors:
        print("\n错误详情:")
        for path, msg in errors:
            print(f"  - {path}")
            print(f"    {msg}")


if __name__ == "__main__":
    main()
