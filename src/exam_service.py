"""
试卷服务 - 处理试卷相关的业务逻辑
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logger import exam_logger
from src.exceptions import ExamNotFoundException, DataLoadException


class ExamService:
    """试卷服务类"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._exam_cache = {}
    
    def get_all_exams(self) -> List[Dict[str, Any]]:
        """获取所有试卷列表（支持从子目录中读取）"""
        exams = []
        
        # 方法1: 从子目录中读取（新结构：n1/, n2/, n3/, n4/, n5/）
        for level_dir in self.data_dir.glob("n[1-5]"):
            if level_dir.is_dir():
                for file_path in level_dir.glob("*.json"):
                    try:
                        exam_info = self._get_exam_info(file_path)
                        if exam_info:
                            exams.append(exam_info)
                    except Exception as e:
                        print(f"读取试卷失败 {file_path}: {e}")
                        continue
        
        # 方法2: 从根目录读取（兼容旧结构）
        for file_path in self.data_dir.glob("*.json"):
            try:
                exam_info = self._get_exam_info(file_path)
                if exam_info:
                    exams.append(exam_info)
            except Exception as e:
                print(f"读取试卷失败 {file_path}: {e}")
                continue
        
        # 按级别、年份、月份排序
        exams.sort(key=lambda x: (x["level"], -int(x["year"]), -int(x["session"])))
        return exams
    
    def get_exams_by_level(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取按级别分组的试卷列表"""
        all_exams = self.get_all_exams()
        exams_by_level = {}
        
        for exam in all_exams:
            level = exam["level"]
            if level not in exams_by_level:
                exams_by_level[level] = []
            exams_by_level[level].append(exam)
        
        return exams_by_level
    
    def get_exam(self, exam_id: str) -> Dict[str, Any]:
        """
        获取单个试卷的完整数据（支持从子目录中读取）
        
        Raises:
            ExamNotFoundException: 试卷不存在
            DataLoadException: 数据加载失败
        """
        # 检查缓存
        if exam_id in self._exam_cache:
            return self._exam_cache[exam_id]
        
        # 尝试从多个位置查找试卷文件
        file_path = None
        
        # 方法1: 根据exam_id推断级别，从对应子目录查找（新结构）
        # exam_id格式: N1_2015_07
        parts = exam_id.split('_')
        if len(parts) >= 1:
            level = parts[0].lower()  # n1, n2, n3, n4, n5
            level_path = self.data_dir / level / f"{exam_id}.json"
            if level_path.exists():
                file_path = level_path
        
        # 方法2: 从根目录查找（兼容旧结构）
        if not file_path:
            root_path = self.data_dir / f"{exam_id}.json"
            if root_path.exists():
                file_path = root_path
        
        # 方法3: 遍历所有子目录查找
        if not file_path:
            for level_dir in self.data_dir.glob("n[1-5]"):
                if level_dir.is_dir():
                    candidate_path = level_dir / f"{exam_id}.json"
                    if candidate_path.exists():
                        file_path = candidate_path
                        break
        
        if not file_path:
            exam_logger.warning(f"试卷不存在: {exam_id}")
            raise ExamNotFoundException(exam_id)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                exam_data = json.load(f)
                # 缓存数据
                self._exam_cache[exam_id] = exam_data
                exam_logger.info(f"加载试卷成功: {exam_id} (from {file_path})")
                return exam_data
        except json.JSONDecodeError as e:
            exam_logger.error(f"试卷 JSON 解析失败 {exam_id}: {e}")
            raise DataLoadException("试卷数据", f"JSON 格式错误: {str(e)}")
        except Exception as e:
            exam_logger.error(f"读取试卷失败 {exam_id}: {e}")
            raise DataLoadException("试卷数据", str(e))
    
    def _get_exam_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """从文件中提取试卷基本信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                exam_data = json.load(f)
                exam_info = exam_data.get("exam_info", {})
                
                # 计算题目总数
                question_count = 0
                for section in exam_info.get("sections", []):
                    for passage in section.get("passages", []):
                        question_count += len(passage.get("questions", []))
                
                # 解析文件名
                parts = file_path.stem.split('_')
                level = parts[0] if len(parts) > 0 else ""
                year = parts[1] if len(parts) > 1 else ""
                session = parts[2] if len(parts) > 2 else ""
                
                return {
                    "id": file_path.stem,
                    "title": exam_info.get("title", file_path.stem),
                    "questionCount": question_count,
                    "level": level,
                    "year": year,
                    "session": session,
                    "display": f"{year}_{session}",
                    "checked": exam_info.get("checked", False)
                }
        except Exception as e:
            print(f"解析试卷信息失败 {file_path}: {e}")
            return None
