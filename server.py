#!/usr/bin/env python3
"""
在线试卷系统 - FastAPI 后端服务器
基于原 exam-viewer 改造，保持原有样式和功能
"""

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import sys
from pathlib import Path
from typing import List, Dict, Any
import uvicorn

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.logger import app_logger
from src.models import *
from src.exceptions import AppException
from src.middleware import exception_handler, logging_middleware
from src.exam_service import ExamService
from src.answer_service import AnswerService
from src.auth_service import AuthService
from src.furigana_service import FuriganaService
from src.statistics_service import StatisticsService
from src.user_service import UserService

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# 注册异常处理器
app.add_exception_handler(AppException, exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler)
app.add_exception_handler(StarletteHTTPException, exception_handler)
app.add_exception_handler(Exception, exception_handler)

# 添加日志中间件
app.middleware("http")(logging_middleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Jinja2 模板配置
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# 初始化服务
exam_service = ExamService(settings.DATA_DIR)
answer_service = AnswerService(settings.DATA_DIR)
auth_service = AuthService(settings.DATA_DIR)
furigana_service = FuriganaService(settings.FURIGANA_DICT_PATH)
statistics_service = StatisticsService(settings.DATA_DIR)
user_service = UserService(settings.DATA_DIR)



@app.get("/")
async def root(request: Request):
    """返回主页（使用模板渲染）"""
    try:
        # 使用服务获取分组的试卷列表
        exams_by_level = exam_service.get_exams_by_level()
        
        # 使用模板渲染
        return templates.TemplateResponse("index.html", {
            "request": request,
            "exams_by_level": exams_by_level,
            "levels": ["N1", "N2", "N3", "N4", "N5"]
        })
    except Exception as e:
        app_logger.error(f"模板渲染失败: {e}")
        # 降级到静态文件
        index_file = settings.STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": settings.APP_NAME, "status": "running", "error": str(e)}


@app.get("/favicon.ico")
async def favicon():
    """返回 favicon"""
    from fastapi.responses import Response
    # 使用资源目录中的图标
    icon_file = settings.STATIC_DIR / "resource" / "icons" / "icon.png"
    if icon_file.exists():
        return FileResponse(icon_file)
    # 如果没有图标，返回 204 No Content
    return Response(status_code=204)


@app.get("/resource/{path:path}")
async def get_resource(path: str):
    """提供资源文件（音频、图片等）"""
    import mimetypes
    from src.exceptions import ResourceNotFoundException
    
    resource_file = settings.STATIC_DIR / "resource" / path
    
    if not resource_file.exists():
        raise ResourceNotFoundException("资源文件", path)
    
    # 根据文件扩展名设置 MIME 类型
    mime_type, _ = mimetypes.guess_type(str(resource_file))
    
    return FileResponse(
        resource_file,
        media_type=mime_type or "application/octet-stream"
    )


@app.get("/api/exams", response_model=List[ExamInfo])
async def get_exams(
    level: Optional[str] = None,
    year: Optional[str] = None,
    sort: str = "date_desc"
) -> List[Dict[str, Any]]:
    """
    获取试卷列表
    
    Args:
        level: 级别过滤 (N1, N2, N3, N4, N5)
        year: 年份过滤
        sort: 排序方式 (date_desc, date_asc, level)
    """
    exams = exam_service.get_all_exams()
    
    # 过滤
    if level:
        exams = [e for e in exams if e.get("level") == level]
    
    if year:
        exams = [e for e in exams if e.get("year") == year]
    
    # 排序
    if sort == "date_desc":
        exams.sort(key=lambda x: (x.get("year", ""), x.get("session", "")), reverse=True)
    elif sort == "date_asc":
        exams.sort(key=lambda x: (x.get("year", ""), x.get("session", "")))
    elif sort == "level":
        exams.sort(key=lambda x: x.get("level", ""))
    
    return exams


@app.get("/api/exams/{exam_id}")
async def get_exam(exam_id: str) -> Dict[str, Any]:
    """获取单个试卷详情"""
    return exam_service.get_exam(exam_id)


@app.post("/api/exams", response_model=SuccessResponse)
async def create_exam(exam_data: ExamCreateRequest) -> SuccessResponse:
    """创建或更新试卷"""
    import time
    import json
    from src.exceptions import DataSaveException
    
    try:
        exam_id = exam_data.id or f"exam_{int(time.time() * 1000)}"
        file_path = settings.DATA_DIR / f"{exam_id}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(exam_data.dict(), f, ensure_ascii=False, indent=2)

        app_logger.info(f"试卷保存成功: {exam_id}")
        return SuccessResponse(message="试卷保存成功", data={"id": exam_id})
    except Exception as e:
        app_logger.error(f"保存试卷失败: {e}")
        raise DataSaveException("试卷", str(e))


@app.delete("/api/exams/{exam_id}", response_model=SuccessResponse)
async def delete_exam(exam_id: str) -> SuccessResponse:
    """删除试卷"""
    from src.exceptions import ExamNotFoundException, DataSaveException
    
    file_path = settings.DATA_DIR / f"{exam_id}.json"

    if not file_path.exists():
        raise ExamNotFoundException(exam_id)

    try:
        file_path.unlink()
        app_logger.info(f"试卷删除成功: {exam_id}")
        return SuccessResponse(message="试卷删除成功")
    except Exception as e:
        app_logger.error(f"删除试卷失败: {e}")
        raise DataSaveException("试卷", str(e))


# ==================== 答案相关 API ====================

@app.post("/api/answers/submit", response_model=ScoreResult)
async def submit_answers(data: AnswerSubmitRequest) -> ScoreResult:
    """提交答案并评分"""
    # 获取试卷数据
    exam_data = exam_service.get_exam(data.exam_id)
    
    # 计算得分
    result = answer_service.calculate_score(data.exam_id, data.answers, exam_data)
    
    # 保存答案和统计信息
    answer_service.save_answers(data.user_id, data.exam_id, data.answers, result)
    
    app_logger.info(f"答案提交成功: user={data.user_id}, exam={data.exam_id}, score={result['score']}")
    
    return ScoreResult(**result)


@app.get("/api/answers/{user_id}/{exam_id}", response_model=AnswersResponse)
async def get_answers(user_id: str, exam_id: str) -> AnswersResponse:
    """获取用户答案"""
    answers = answer_service.load_answers(user_id, exam_id)
    return AnswersResponse(answers=answers)


@app.get("/api/progress/{user_id}", response_model=ProgressResponse)
async def get_progress(user_id: str) -> ProgressResponse:
    """获取用户学习进度"""
    progress = answer_service.get_user_progress(user_id)
    return ProgressResponse(**progress)


@app.get("/api/progress/{user_id}/exams")
async def get_exam_progress(user_id: str) -> Dict[str, float]:
    """获取用户所有试卷的完成度 {exam_id: 0.0~1.0}"""
    return answer_service.get_all_exam_progress(user_id)


# ==================== 认证相关 API ====================

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(data: LoginRequest) -> AuthResponse:
    """用户登录"""
    result = auth_service.login(data.username, data.password)
    return AuthResponse(**result)


@app.post("/api/auth/register", response_model=SuccessResponse)
async def register(data: RegisterRequest) -> SuccessResponse:
    """用户注册"""
    result = auth_service.register(data.username, data.password, data.email)
    return SuccessResponse(message="注册成功", data=result)


@app.post("/api/auth/logout", response_model=SuccessResponse)
async def logout(data: LogoutRequest) -> SuccessResponse:
    """用户登出"""
    success = auth_service.logout(data.token)
    return SuccessResponse(message="登出成功" if success else "登出失败")


@app.get("/api/auth/verify", response_model=TokenVerifyResponse)
async def verify_token(token: str) -> TokenVerifyResponse:
    """验证token"""
    result = auth_service.verify_token(token)
    return TokenVerifyResponse(**result)


# ==================== 统计相关 API ====================

@app.get("/api/statistics/{user_id}", response_model=UserStatistics)
async def get_statistics(user_id: str) -> UserStatistics:
    """获取用户统计数据"""
    stats = statistics_service.get_user_statistics(user_id)
    return UserStatistics(**stats)


@app.get("/api/statistics/{user_id}/weak-points", response_model=List[WeakPoint])
async def get_weak_points(user_id: str) -> List[WeakPoint]:
    """获取用户薄弱点"""
    weak_points = statistics_service.get_weak_points(user_id)
    return [WeakPoint(**wp) for wp in weak_points]


@app.get("/api/statistics/{user_id}/learning-curve", response_model=List[LearningCurvePoint])
async def get_learning_curve(user_id: str, days: int = 30) -> List[LearningCurvePoint]:
    """获取学习曲线"""
    curve = statistics_service.get_learning_curve(user_id, days)
    return [LearningCurvePoint(**point) for point in curve]


@app.get("/api/statistics/{user_id}/recommendations")
async def get_recommendations(user_id: str, limit: int = 5) -> List[str]:
    """获取推荐试卷"""
    return statistics_service.recommend_exams(user_id, limit)


# ==================== 用户相关 API ====================

@app.get("/api/users/{user_id}")
async def get_user(user_id: str) -> Dict[str, Any]:
    """获取用户信息"""
    return user_service.get_user(user_id)


@app.get("/api/users/by-role/{role_id}")
async def get_users_by_role(role_id: str) -> List[Dict[str, Any]]:
    """获取指定角色的用户列表"""
    return user_service.get_users_by_role(role_id)


@app.get("/api/users/{user_id}/permissions")
async def get_user_permissions(user_id: str) -> Dict[str, Any]:
    """获取用户权限（可见的功能和区域）"""
    return user_service.get_user_permissions(user_id)


@app.get("/api/roles")
async def get_all_roles() -> Dict[str, Any]:
    """获取所有角色定义"""
    return user_service.get_all_roles()


# ==================== 振假名相关 API ====================

@app.post("/api/furigana/add", response_model=FuriganaResponse)
async def add_furigana(data: FuriganaRequest) -> FuriganaResponse:
    """为文本添加振假名"""
    result = furigana_service.add_furigana(data.text)
    return FuriganaResponse(result=result)


@app.get("/api/furigana/reading/{word}", response_model=ReadingResponse)
async def get_reading(word: str) -> ReadingResponse:
    """获取单词读音"""
    reading = furigana_service.get_reading(word)
    return ReadingResponse(word=word, reading=reading)


# ==================== 挂载静态文件（必须放在所有路由之后） ====================
# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
# 挂载data目录（包含image、audio、paper等子目录）
app.mount("/data", StaticFiles(directory=str(settings.BASE_DIR / "data")), name="data")


if __name__ == "__main__":
    app_logger.info("=" * 60)
    app_logger.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    app_logger.info(f"📁 数据目录: {settings.DATA_DIR}")
    app_logger.info(f"📁 静态文件目录: {settings.STATIC_DIR}")
    app_logger.info(f"🌐 访问地址: http://{settings.HOST}:{settings.PORT}")
    app_logger.info(f"🔧 调试模式: {'开启' if settings.DEBUG else '关闭'}")
    app_logger.info(f"📝 日志级别: {settings.LOG_LEVEL}")
    app_logger.info("=" * 60)

    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
