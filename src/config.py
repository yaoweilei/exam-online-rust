"""
配置管理 - 统一的配置文件
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "在线试卷系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # 目录配置
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data" / "paper" / "jlpt"  # 试卷根目录
    USER_DATA_DIR: Path = BASE_DIR / "data" / "user"
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    
    # 图片和音频目录（已按级别分类）
    IMAGE_DIR: Path = BASE_DIR / "data" / "image" / "jlpt"
    AUDIO_DIR: Path = BASE_DIR / "data" / "audio" / "jlpt"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 6
    
    # CORS 配置
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # 日志配置
    # 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
    # DEBUG: 详细的调试信息
    # INFO: 一般信息（默认）
    # WARNING: 警告信息
    # ERROR: 错误信息
    # CRITICAL: 严重错误
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 数据库配置（预留）
    DATABASE_URL: Optional[str] = None
    
    # Redis 配置（预留）
    REDIS_URL: Optional[str] = None
    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".json", ".mp3", ".wav", ".jpg", ".png"]
    
    # 振假名字典路径
    FURIGANA_DICT_PATH: Path = STATIC_DIR / "resource" / "furigana.dict.json"
    
    # 环境配置
    ENV: str = "development"  # development 或 production
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的字段，避免验证错误
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.STATIC_DIR.mkdir(parents=True, exist_ok=True)


# 创建全局配置实例
settings = Settings()


# 开发环境配置
class DevelopmentSettings(Settings):
    """开发环境配置"""
    DEBUG: bool = True
    RELOAD: bool = True
    LOG_LEVEL: str = "DEBUG"  # 开发环境显示所有日志


# 生产环境配置
class ProductionSettings(Settings):
    """生产环境配置"""
    DEBUG: bool = False
    RELOAD: bool = False
    LOG_LEVEL: str = "WARNING"  # 生产环境只显示警告和错误
    CORS_ORIGINS: list = ["https://yourdomain.com"]


def get_settings() -> Settings:
    """根据环境变量获取配置"""
    env = os.getenv("ENV", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()
