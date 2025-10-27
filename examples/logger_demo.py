"""
日志模块使用示例

演示如何在项目中使用日志系统
"""

from src.utils.logger import get_logger

# 获取 logger 实例
logger = get_logger()

def demo_logging():
    """演示不同级别的日志输出"""
    
    logger.debug("这是 DEBUG 级别日志：用于详细的调试信息")
    logger.info("这是 INFO 级别日志：一般信息（策略信号、订单提交）")
    logger.warning("这是 WARNING 级别日志：警告信息（重试、异常恢复）")
    logger.error("这是 ERROR 级别日志：错误信息（订单失败、API 错误）")
    logger.critical("这是 CRITICAL 级别日志：严重错误（模块崩溃、连接断开）")
    
    # 演示中文日志
    logger.info("订单已创建：交易对 BTC/USDT，数量 0.01")
    logger.warning("风险提示：当前持仓已达到上限")
    logger.error("API 调用失败：连接超时")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("日志系统演示开始")
    logger.info("=" * 50)
    
    demo_logging()
    
    logger.info("=" * 50)
    logger.info("日志系统演示结束")
    logger.info("=" * 50)

