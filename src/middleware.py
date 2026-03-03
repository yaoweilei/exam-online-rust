"""
中间件 - 统一的异常处理和请求处理
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.exceptions import AppException
from src.logger import app_logger
import traceback


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    统一异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSON 响应
    """
    # 记录请求信息
    app_logger.error(
        f"异常发生 - 路径: {request.url.path}, "
        f"方法: {request.method}, "
        f"异常: {type(exc).__name__}: {str(exc)}"
    )
    
    # 自定义应用异常
    if isinstance(exc, AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "code": exc.code,
                "detail": exc.detail
            }
        )
    
    # FastAPI 验证错误
    if isinstance(exc, RequestValidationError):
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "请求参数验证失败",
                "code": "ValidationError",
                "detail": "; ".join(errors)
            }
        )
    
    # Starlette HTTP 异常
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "code": "HTTPException"
            }
        )
    
    # 未知异常
    app_logger.error(f"未处理的异常: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "服务器内部错误",
            "code": "InternalServerError",
            "detail": str(exc) if app_logger.level <= 10 else None  # DEBUG 模式下显示详情
        }
    )


async def logging_middleware(request: Request, call_next):
    """
    请求日志中间件
    
    Args:
        request: 请求对象
        call_next: 下一个处理器
        
    Returns:
        响应对象
    """
    # 记录请求
    app_logger.info(
        f"请求开始 - {request.method} {request.url.path} "
        f"客户端: {request.client.host if request.client else 'unknown'}"
    )
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应
    app_logger.info(
        f"请求完成 - {request.method} {request.url.path} "
        f"状态码: {response.status_code}"
    )
    
    return response
