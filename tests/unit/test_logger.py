"""
日志模块单元测试

测试日志配置的正确性，包括：
- 日志文件创建
- 日志格式验证
- 日志级别测试
"""

import pytest
from pathlib import Path
import time
from src.utils.logger import get_logger, setup_logger


class TestLogger:
    """日志模块测试类"""
    
    def test_logger_instance(self):
        """测试获取 logger 实例"""
        logger = get_logger()
        assert logger is not None, "logger 实例不应为 None"
    
    def test_log_file_creation(self, tmp_path):
        """测试日志文件是否正确创建"""
        # 使用临时目录进行测试
        test_log_dir = tmp_path / "test_logs"
        test_log_file = "test.log"
        
        # 重新配置 logger 使用测试目录
        setup_logger(log_dir=str(test_log_dir), log_file=test_log_file)
        logger = get_logger()
        
        # 写入测试日志
        logger.info("测试日志文件创建")
        
        # 等待日志写入
        time.sleep(0.1)
        
        # 验证日志文件是否创建
        log_file_path = test_log_dir / test_log_file
        assert log_file_path.exists(), f"日志文件应该被创建: {log_file_path}"
    
    def test_log_levels(self, tmp_path):
        """测试不同日志级别"""
        test_log_dir = tmp_path / "test_logs_levels"
        test_log_file = "test_levels.log"
        
        setup_logger(log_dir=str(test_log_dir), log_file=test_log_file)
        logger = get_logger()
        
        # 测试不同级别的日志
        logger.debug("这是 DEBUG 级别日志")
        logger.info("这是 INFO 级别日志")
        logger.warning("这是 WARNING 级别日志")
        logger.error("这是 ERROR 级别日志")
        
        # 等待日志写入
        time.sleep(0.1)
        
        # 读取日志文件内容
        log_file_path = test_log_dir / test_log_file
        assert log_file_path.exists(), "日志文件应该存在"
        
        log_content = log_file_path.read_text(encoding="utf-8")
        
        # 验证日志内容包含不同级别
        assert "DEBUG" in log_content, "日志应包含 DEBUG 级别"
        assert "INFO" in log_content, "日志应包含 INFO 级别"
        assert "WARNING" in log_content, "日志应包含 WARNING 级别"
        assert "ERROR" in log_content, "日志应包含 ERROR 级别"
    
    def test_log_format(self, tmp_path):
        """测试日志格式是否符合要求：时间 | 等级 | 文件名:行号 | 信息"""
        test_log_dir = tmp_path / "test_logs_format"
        test_log_file = "test_format.log"

        setup_logger(log_dir=str(test_log_dir), log_file=test_log_file)
        logger = get_logger()

        test_message = "测试日志格式"
        logger.info(test_message)

        # 等待日志写入
        time.sleep(0.1)

        # 读取日志文件
        log_file_path = test_log_dir / test_log_file
        log_content = log_file_path.read_text(encoding="utf-8")

        # 验证日志格式包含必要元素
        assert "|" in log_content, "日志格式应包含分隔符 |"
        assert "INFO" in log_content, "日志应包含级别信息"
        assert test_message in log_content, "日志应包含消息内容"
        assert "test_log_format" in log_content, "日志应包含函数名"
        assert ":" in log_content, "日志应包含行号分隔符"

        # 验证日志格式符合：时间 | 等级 | 模块:函数:行号 | 信息
        lines = log_content.strip().split("\n")
        for line in lines:
            if test_message in line:
                parts = line.split("|")
                assert len(parts) == 4, "日志应包含4个部分（时间、等级、位置、信息）"
    
    def test_chinese_support(self, tmp_path):
        """测试中文日志支持"""
        test_log_dir = tmp_path / "test_logs_chinese"
        test_log_file = "test_chinese.log"
        
        setup_logger(log_dir=str(test_log_dir), log_file=test_log_file)
        logger = get_logger()
        
        chinese_message = "这是一条中文日志消息：订单已创建"
        logger.info(chinese_message)
        
        # 等待日志写入
        time.sleep(0.1)
        
        # 读取日志文件
        log_file_path = test_log_dir / test_log_file
        log_content = log_file_path.read_text(encoding="utf-8")
        
        # 验证中文内容正确写入
        assert chinese_message in log_content, "日志应正确支持中文"

