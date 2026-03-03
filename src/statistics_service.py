"""
统计服务 - 处理学习数据统计和分析
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from datetime import datetime, timedelta
from collections import defaultdict
from src.logger import statistics_logger
from src.exceptions import DataLoadException


class StatisticsService:
    """统计服务类"""
    
    def __init__(self, data_dir: Path):
        self.answers_dir = data_dir.parent / "user" / "answers"
        self.answers_dir.mkdir(parents=True, exist_ok=True)
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户统计数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计数据
        """
        user_dir = self.answers_dir / user_id
        
        if not user_dir.exists():
            return self._empty_statistics()
        
        total_exams = 0
        total_questions = 0
        correct_answers = 0
        wrong_answers = 0
        
        exams_data = []
        
        for answer_file in user_dir.glob("*.json"):
            try:
                with open(answer_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                total_exams += 1
                answers = data.get("answers", {})
                
                # 这里需要加载对应的试卷数据来验证答案
                # 简化版本：假设答案文件中包含统计信息
                if "statistics" in data:
                    stats = data["statistics"]
                    total_questions += stats.get("total_questions", 0)
                    correct_answers += stats.get("correct_count", 0)
                    wrong_answers += stats.get("wrong_count", 0)
                    
                    exams_data.append({
                        "exam_id": data.get("exam_id"),
                        "score": stats.get("score", 0),
                        "accuracy": stats.get("accuracy", 0),
                        "completed_at": data.get("saved_at")
                    })
            except Exception as e:
                statistics_logger.warning(f"读取答案文件失败 {answer_file}: {e}")
                continue
        
        # 计算总体统计
        overall_accuracy = (correct_answers / (correct_answers + wrong_answers) * 100) if (correct_answers + wrong_answers) > 0 else 0
        average_score = sum(e["score"] for e in exams_data) / len(exams_data) if exams_data else 0
        
        return {
            "user_id": user_id,
            "total_exams": total_exams,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "wrong_answers": wrong_answers,
            "overall_accuracy": round(overall_accuracy, 2),
            "average_score": round(average_score, 2),
            "exams": exams_data
        }
    
    def get_weak_points(self, user_id: str) -> List[Dict[str, Any]]:
        """
        分析用户薄弱点
        
        Args:
            user_id: 用户ID
            
        Returns:
            薄弱点列表
        """
        user_dir = self.answers_dir / user_id
        
        if not user_dir.exists():
            return []
        
        # 按题型统计错误率
        section_stats = defaultdict(lambda: {"total": 0, "wrong": 0})
        
        for answer_file in user_dir.glob("*.json"):
            try:
                with open(answer_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "results" in data.get("statistics", {}):
                    results = data["statistics"]["results"]
                    
                    for question_id, result in results.items():
                        # 这里需要知道题目属于哪个章节
                        # 简化版本：从 question_id 推断
                        section = self._infer_section(question_id)
                        section_stats[section]["total"] += 1
                        
                        if result.get("status") == "wrong":
                            section_stats[section]["wrong"] += 1
            except Exception as e:
                print(f"分析答案文件失败 {answer_file}: {e}")
                continue
        
        # 计算错误率并排序
        weak_points = []
        for section, stats in section_stats.items():
            if stats["total"] > 0:
                error_rate = stats["wrong"] / stats["total"] * 100
                weak_points.append({
                    "section": section,
                    "total_questions": stats["total"],
                    "wrong_count": stats["wrong"],
                    "error_rate": round(error_rate, 2)
                })
        
        # 按错误率降序排序
        weak_points.sort(key=lambda x: x["error_rate"], reverse=True)
        
        return weak_points
    
    def get_learning_curve(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取学习曲线数据
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            学习曲线数据
        """
        user_dir = self.answers_dir / user_id
        
        if not user_dir.exists():
            return []
        
        # 按日期统计
        daily_stats = defaultdict(lambda: {
            "date": "",
            "exams_count": 0,
            "questions_count": 0,
            "correct_count": 0,
            "average_score": 0,
            "scores": []
        })
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for answer_file in user_dir.glob("*.json"):
            try:
                with open(answer_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                saved_at = data.get("saved_at")
                if not saved_at:
                    continue
                
                saved_date = datetime.fromisoformat(saved_at)
                if saved_date < cutoff_date:
                    continue
                
                date_key = saved_date.strftime("%Y-%m-%d")
                
                if "statistics" in data:
                    stats = data["statistics"]
                    daily_stats[date_key]["date"] = date_key
                    daily_stats[date_key]["exams_count"] += 1
                    daily_stats[date_key]["questions_count"] += stats.get("total_questions", 0)
                    daily_stats[date_key]["correct_count"] += stats.get("correct_count", 0)
                    daily_stats[date_key]["scores"].append(stats.get("score", 0))
            except Exception as e:
                print(f"处理学习曲线数据失败 {answer_file}: {e}")
                continue
        
        # 计算平均分
        curve_data = []
        for date_key in sorted(daily_stats.keys()):
            stats = daily_stats[date_key]
            scores = stats["scores"]
            stats["average_score"] = round(sum(scores) / len(scores), 2) if scores else 0
            del stats["scores"]
            curve_data.append(stats)
        
        return curve_data
    
    def recommend_exams(self, user_id: str, limit: int = 5) -> List[str]:
        """
        推荐试卷
        
        Args:
            user_id: 用户ID
            limit: 推荐数量
            
        Returns:
            推荐的试卷ID列表
        """
        # 基于薄弱点推荐
        weak_points = self.get_weak_points(user_id)
        
        # 简化版本：返回空列表
        # 实际应该根据薄弱点查找相关试卷
        return []
    
    def _empty_statistics(self) -> Dict[str, Any]:
        """返回空统计数据"""
        return {
            "total_exams": 0,
            "total_questions": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
            "overall_accuracy": 0,
            "average_score": 0,
            "exams": []
        }
    
    def _infer_section(self, question_id: str) -> str:
        """从题目ID推断章节"""
        # 简化版本：从ID格式推断
        # 实际应该从试卷数据中查找
        if "vocab" in question_id.lower():
            return "词汇"
        elif "grammar" in question_id.lower():
            return "语法"
        elif "reading" in question_id.lower():
            return "阅读"
        elif "listening" in question_id.lower():
            return "听力"
        else:
            return "未知"
