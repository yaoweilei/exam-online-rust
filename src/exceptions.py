"""
自定义异常 - 统一的异常处理
"""

from typing import Optional


class AppException(Exception):
    """应用基础异常"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: Optional[str] = None,
        detail: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or self.__class__.__name__
        self.detail = detail
        super().__init__(self.message)


# ==================== 认证相关异常 ====================

class AuthException(AppException):
    """认证异常基类"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, status_code=401, detail=detail)


class InvalidCredentialsException(AuthException):
    """无效凭证"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__("用户名或密码错误", detail=detail)


class TokenExpiredException(AuthException):
    """Token 过期"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__("Token 已过期", detail=detail)


class TokenInvalidException(AuthException):
    """Token 无效"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__("Token 无效", detail=detail)


class UserExistsException(AppException):
    """用户已存在"""
    def __init__(self, username: str):
        super().__init__(
            f"用户名 '{username}' 已存在",
            status_code=400,
            detail="请使用其他用户名"
        )


class PermissionDeniedException(AppException):
    """权限不足"""
    def __init__(self, permission: str):
        super().__init__(
            "权限不足",
            status_code=403,
            detail=f"需要权限: {permission}"
        )


# ==================== 资源相关异常 ====================

class ResourceNotFoundException(AppException):
    """资源不存在"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} 不存在",
            status_code=404,
            detail=f"ID: {resource_id}"
        )


class ExamNotFoundException(ResourceNotFoundException):
    """试卷不存在"""
    def __init__(self, exam_id: str):
        super().__init__("试卷", exam_id)


class UserNotFoundException(ResourceNotFoundException):
    """用户不存在"""
    def __init__(self, user_id: str):
        super().__init__("用户", user_id)


# ==================== 数据相关异常 ====================

class DataException(AppException):
    """数据异常基类"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, status_code=500, detail=detail)


class DataLoadException(DataException):
    """数据加载失败"""
    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(f"加载 {resource} 失败", detail=detail)


class DataSaveException(DataException):
    """数据保存失败"""
    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(f"保存 {resource} 失败", detail=detail)


# ==================== 验证相关异常 ====================

class ValidationException(AppException):
    """验证异常"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, status_code=400, detail=detail)


class MissingParameterException(ValidationException):
    """缺少参数"""
    def __init__(self, parameter: str):
        super().__init__(
            "缺少必需参数",
            detail=f"参数: {parameter}"
        )


class InvalidParameterException(ValidationException):
    """无效参数"""
    def __init__(self, parameter: str, reason: str):
        super().__init__(
            f"参数 '{parameter}' 无效",
            detail=reason
        )
