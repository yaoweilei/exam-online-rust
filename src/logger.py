"""
日志系统 - 统一的日志管理
支持日志级别控制：DEBUG < INFO < WARNING < ERROR < CRITICAL
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from src.config import settings


class Logger:
    """日志管理器"""
    
    _loggers = {}
    _initialized = False
    
    # 日志级别映射（标准化）
    LEVEL_MAP = {
        'DEBUG': logging.DEBUG,      # 10
        'INFO': logging.INFO,        # 20
        'WARN': logging.WARNING,     # 30
        'WARNING': logging.WARNING,  # 30
        'ERROR': logging.ERROR,      # 40
        'CRITICAL': logging.CRITICAL # 50
    }
    
    @classmethod
    def _get_log_level(cls) -> int:
        """
        获取日志级别
        
        Returns:
            日志级别（整数）
        """
        level_str = settings.LOG_LEVEL.upper()
        return cls.LEVEL_MAP.get(level_str, logging.INFO)
    
    @classmethod
    def _init_logging(cls):
        """初始化日志系统（只执行一次）"""
        if cls._initialized:
            return
        
        # 设置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(cls._get_log_level())
        
        # 清除已有的处理器
        root_logger.handlers.clear()
        
        cls._initialized = True
        
        # 输出日志级别信息
        level_name = logging.getLevelName(cls._get_log_level())
        print(f"[Logger] 日志级别设置为: {level_name}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            日志记录器实例
        """
        # 确保日志系统已初始化
        cls._init_logging()
        
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(cls._get_log_level())
        
        # 避免重复添加处理器
        if not logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(cls._get_log_level())
            
            # 自定义格式化器（带颜色）
            console_formatter = ColoredFormatter(settings.LOG_FORMAT)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件处理器（如果配置了日志文件）
            if settings.LOG_FILE:
                log_file = Path(settings.LOG_FILE)
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(
                    log_file,
                    encoding='utf-8'
                )
                file_handler.setLevel(cls._get_log_level())
                file_formatter = logging.Formatter(settings.LOG_FORMAT)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        
        # 防止日志传播到根记录器（避免重复输出）
        logger.propagate = False
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def set_level(cls, level: str):
        """
        动态设置日志级别
        
        Args:
            level: 日志级别字符串（DEBUG, INFO, WARN, ERROR, CRITICAL）
        """
        level_int = cls.LEVEL_MAP.get(level.upper(), logging.INFO)
        
        # 更新所有已创建的日志记录器
        for logger in cls._loggers.values():
            logger.setLevel(level_int)
            for handler in logger.handlers:
                handler.setLevel(level_int)
        
        print(f"[Logger] 日志级别已更新为: {logging.getLevelName(level_int)}")


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（仅在终端中显示颜色）"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        # 检查是否支持颜色（Windows 可能不支持）
        if sys.platform == 'win32':
            # Windows 10+ 支持 ANSI 颜色
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                # 不支持颜色，使用普通格式
                return super().format(record)
        
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


# 创建默认日志记录器
app_logger = Logger.get_logger("app")
auth_logger = Logger.get_logger("auth")
exam_logger = Logger.get_logger("exam")
answer_logger = Logger.get_logger("answer")
statistics_logger = Logger.get_logger("statistics")
