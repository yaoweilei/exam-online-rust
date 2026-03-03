"""
数据模型 - Pydantic 模型定义
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, Dict, List, Any
from datetime import datetime


# ==================== 认证相关模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[EmailStr] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v


class LogoutRequest(BaseModel):
    """登出请求"""
    token: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    """认证响应"""
    user_id: str
    username: str
    roles: List[str]
    token: str


class TokenVerifyResponse(BaseModel):
    """Token 验证响应"""
    user_id: str
    username: str
    expires_at: str


# ==================== 试卷相关模型 ====================

class ExamInfo(BaseModel):
    """试卷基本信息"""
    id: str
    title: str
    questionCount: int
    level: str
    year: str
    session: str
    display: str


class ExamCreateRequest(BaseModel):
    """创建试卷请求"""
    id: Optional[str] = None
    exam_info: Dict[str, Any]


# ==================== 答案相关模型 ====================

class AnswerSubmitRequest(BaseModel):
    """提交答案请求"""
    user_id: str = Field(default="guest")
    exam_id: str = Field(..., min_length=1)
    answers: Dict[str, str] = Field(default_factory=dict)


class QuestionResult(BaseModel):
    """单题结果"""
    status: str  # correct, wrong, unanswered
    user_answer: Optional[str] = None
    correct_answer: str


class ScoreResult(BaseModel):
    """评分结果"""
    exam_id: str
    total_questions: int
    correct_count: int
    wrong_count: int
    unanswered_count: int
    score: float
    accuracy: float
    completion: float
    results: Dict[str, QuestionResult]
    timestamp: str


class AnswersResponse(BaseModel):
    """答案响应"""
    answers: Dict[str, str]


class ProgressResponse(BaseModel):
    """进度响应"""
    total_exams: int
    completed_exams: int
    total_questions: int
    correct_answers: int


# ==================== 统计相关模型 ====================

class ExamStatistics(BaseModel):
    """单次考试统计"""
    exam_id: str
    score: float
    accuracy: float
    completed_at: str


class UserStatistics(BaseModel):
    """用户统计数据"""
    user_id: str
    total_exams: int
    total_questions: int
    correct_answers: int
    wrong_answers: int
    overall_accuracy: float
    average_score: float
    exams: List[ExamStatistics]


class WeakPoint(BaseModel):
    """薄弱点"""
    section: str
    total_questions: int
    wrong_count: int
    error_rate: float


class LearningCurvePoint(BaseModel):
    """学习曲线数据点"""
    date: str
    exams_count: int
    questions_count: int
    correct_count: int
    average_score: float


# ==================== 振假名相关模型 ====================

class FuriganaRequest(BaseModel):
    """振假名请求"""
    text: str = Field(..., min_length=1)


class FuriganaResponse(BaseModel):
    """振假名响应"""
    result: str


class ReadingResponse(BaseModel):
    """读音响应"""
    word: str
    reading: Optional[str]


# ==================== 用户相关模型 ====================

class UserInfo(BaseModel):
    """用户信息"""
    id: str
    username: str
    roles: List[str]
    email: Optional[str] = None
    created_at: str


class FeatureInfo(BaseModel):
    """功能信息"""
    id: str
    title: str
    icon: str
    required_roles: Optional[List[str]] = None


class SectionInfo(BaseModel):
    """区域信息"""
    id: str
    title: str
    required_roles: Optional[List[str]] = None


class UserPermissions(BaseModel):
    """用户权限"""
    user_id: str
    roles: List[str]
    features: List[FeatureInfo]
    sections: List[SectionInfo]


# ==================== 通用响应模型 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
