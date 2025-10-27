"""
日志配置模块

使用 loguru 实现统一的日志管理，包含：
- 自定义日志格式：时间 | 等级 | 文件名:行号 | 信息
- 按时间轮转：保存3天的日志
- 统一的日志文件输出
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_dir: str = "logs", log_file: str = "st_trading.log") -> None:
    """
    配置全局日志系统
    
    Args:
        log_dir: 日志文件目录，默认为 "logs"
        log_file: 日志文件名，默认为 "st_trading.log"
    
    实现细节：
        - 移除默认的控制台输出配置
        - 添加控制台输出（带颜色）
        - 添加文件输出（按时间轮转，保留3天）
        - 统一日志格式：时间 | 等级 | 文件名:行号 | 信息
    """
    # 移除默认的 logger 配置
    logger.remove()
    
    # 自定义日志格式：时间 | 等级 | 文件名:行号 | 信息
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件日志格式（不带颜色标签）
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台输出（带颜色，方便开发调试）
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG",
        colorize=True,
        backtrace=True,  # 显示完整的堆栈跟踪
        diagnose=True    # 显示变量值，便于调试
    )
    
    # 确保日志目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 添加文件输出（按时间轮转，保留3天）
    logger.add(
        log_path / log_file,
        format=file_format,
        level="DEBUG",
        rotation="00:00",      # 每天午夜轮转
        retention="3 days",    # 保留3天的日志
        compression="zip",     # 压缩旧日志文件
        encoding="utf-8",      # 使用 UTF-8 编码支持中文
        backtrace=True,
        diagnose=True
    )
    
    logger.info("日志系统初始化完成")


def get_logger():
    """
    获取 logger 实例
    
    Returns:
        logger: loguru logger 实例
    
    使用方式：
        from src.utils.logger import get_logger
        logger = get_logger()
        logger.info("这是一条信息日志")
    """
    return logger


# 模块导入时自动初始化日志系统
setup_logger()

