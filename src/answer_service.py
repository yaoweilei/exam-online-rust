"""
答案服务 - 处理答案验证、评分和存储
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from datetime import datetime
from src.logger import answer_logger
from src.exceptions import DataLoadException, DataSaveException


class AnswerService:
    """答案服务类"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.answers_dir = data_dir.parent / "user" / "answers"
        self.answers_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_answer(self, question_id: str, user_answer: str, correct_answer: str) -> bool:
        """
        验证答案是否正确
        
        Args:
            question_id: 题目ID
            user_answer: 用户答案
            correct_answer: 正确答案
            
        Returns:
            是否正确
        """
        # 标准化答案（去除空格、转小写）
        user_answer = str(user_answer).strip().lower()
        correct_answer = str(correct_answer).strip().lower()
        
        return user_answer == correct_answer
    
    def calculate_score(self, exam_id: str, answers: Dict[str, str], exam_data: Dict) -> Dict[str, Any]:
        """
        计算考试得分
        
        Args:
            exam_id: 试卷ID
            answers: 用户答案 {question_id: answer}
            exam_data: 试卷数据
            
        Returns:
            评分结果
        """
        total_questions = 0
        correct_count = 0
        wrong_count = 0
        unanswered_count = 0
        
        results = {}
        
        # 遍历所有题目
        for section in exam_data.get("exam_info", {}).get("sections", []):
            for passage in section.get("passages", []):
                for question in passage.get("questions", []):
                    question_id = question.get("id")
                    correct_answer = question.get("answer")
                    
                    if not question_id or not correct_answer:
                        continue
                    
                    total_questions += 1
                    user_answer = answers.get(str(question_id))
                    
                    if not user_answer:
                        unanswered_count += 1
                        results[question_id] = {
                            "status": "unanswered",
                            "correct_answer": correct_answer
                        }
                    elif self.validate_answer(question_id, user_answer, correct_answer):
                        correct_count += 1
                        results[question_id] = {
                            "status": "correct",
                            "user_answer": user_answer,
                            "correct_answer": correct_answer
                        }
                    else:
                        wrong_count += 1
                        results[question_id] = {
                            "status": "wrong",
                            "user_answer": user_answer,
                            "correct_answer": correct_answer
                        }
        
        # 计算得分
        score = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "exam_id": exam_id,
            "total_questions": total_questions,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "unanswered_count": unanswered_count,
            "score": round(score, 2),
            "accuracy": round(correct_count / (correct_count + wrong_count) * 100, 2) if (correct_count + wrong_count) > 0 else 0,
            "completion": round((correct_count + wrong_count) / total_questions * 100, 2) if total_questions > 0 else 0,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_answers(
        self, 
        user_id: str, 
        exam_id: str, 
        answers: Dict[str, str],
        statistics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        保存用户答案和统计信息
        
        Args:
            user_id: 用户ID
            exam_id: 试卷ID
            answers: 答案字典
            statistics: 统计信息（可选）
            
        Raises:
            DataSaveException: 保存失败
        """
        try:
            user_dir = self.answers_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            answer_file = user_dir / f"{exam_id}.json"
            
            data = {
                "user_id": user_id,
                "exam_id": exam_id,
                "answers": answers,
                "saved_at": datetime.now().isoformat()
            }
            
            # 添加统计信息
            if statistics:
                data["statistics"] = statistics
            
            with open(answer_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            answer_logger.info(f"保存答案成功: user={user_id}, exam={exam_id}")
        except Exception as e:
            answer_logger.error(f"保存答案失败: {e}")
            raise DataSaveException("答案数据", str(e))
    
    def load_answers(self, user_id: str, exam_id: str) -> Dict[str, str]:
        """
        加载用户答案
        
        Args:
            user_id: 用户ID
            exam_id: 试卷ID
            
        Returns:
            答案字典，如果不存在返回空字典
        """
        try:
            answer_file = self.answers_dir / user_id / f"{exam_id}.json"
            
            if not answer_file.exists():
                answer_logger.info(f"答案文件不存在: user={user_id}, exam={exam_id}")
                return {}
            
            with open(answer_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("answers", {})
        except Exception as e:
            answer_logger.error(f"加载答案失败: {e}")
            raise DataLoadException("答案数据", str(e))
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户学习进度
        
        Args:
            user_id: 用户ID
            
        Returns:
            进度统计
        """
        user_dir = self.answers_dir / user_id
        
        if not user_dir.exists():
            return {
                "total_exams": 0,
                "completed_exams": 0,
                "total_questions": 0,
                "correct_answers": 0
            }
        
        total_exams = 0
        completed_exams = 0
        
        for answer_file in user_dir.glob("*.json"):
            total_exams += 1
            # 这里可以添加更详细的统计逻辑
        
        return {
            "total_exams": total_exams,
            "completed_exams": completed_exams,
            "total_questions": 0,  # 需要从答案文件中统计
            "correct_answers": 0   # 需要从答案文件中统计
        }

    def get_all_exam_progress(self, user_id: str) -> Dict[str, float]:
        """
        获取用户所有试卷的学习完成度 (0.0 ~ 1.0)
        
        Returns:
            {exam_id: completion_ratio} 例如 {"N1_2025_07": 0.75}
        """
        user_dir = self.answers_dir / user_id
        if not user_dir.exists():
            return {}
        
        progress = {}
        for answer_file in user_dir.glob("*.json"):
            try:
                with open(answer_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                exam_id = data.get("exam_id", answer_file.stem)
                stats = data.get("statistics", {})
                if stats:
                    # 有统计信息 = 已提交过，用 completion 百分比
                    progress[exam_id] = stats.get("completion", 0) / 100.0
                else:
                    # 只有 answers, 没有 statistics = 还在做题中
                    answers = data.get("answers", {})
                    total = stats.get("total_questions", 0)
                    if total > 0:
                        progress[exam_id] = len(answers) / total
                    elif answers:
                        # 没有 total 信息, 但有答案 = 至少开始了
                        progress[exam_id] = 0.01  # 标记已开始
                    else:
                        progress[exam_id] = 0.0
            except Exception as e:
                answer_logger.error(f"读取进度失败 {answer_file}: {e}")
                continue
        return progress
