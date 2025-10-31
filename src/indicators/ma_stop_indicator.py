"""
MA Stop 指标实现

MA Stop (Moving Average Stop) 是一个基于移动平均线的趋势跟踪指标。

计算逻辑：
1. 计算指定周期的移动平均线（MA）
2. 计算MA的百分比偏移作为止损线
3. 根据价格与止损线的关系判断信号：
   - 价格 > 止损线 → LONG（多头）
   - 价格 < 止损线 → SHORT（空头）
   - 其他 → NONE（无信号）

参数：
- period: MA周期（默认20）
- percent: 止损百分比（默认2，表示2%）

使用示例：
    from src.indicators.ma_stop_indicator import MAStopIndicator
    from src.core.ta.indicator_factory import IndicatorFactory
    
    # 注册指标
    IndicatorFactory.register_indicator("ma_stop_ta", MAStopIndicator)
"""

from typing import Dict, Any, List
from src.core.ta.base_indicator import BaseIndicator, IndicatorSignal
from src.core.event.event_bus import EventBus
from src.utils.logger import logger


class MAStopIndicator(BaseIndicator):
    """
    MA Stop 指标实现
    
    基于移动平均线的趋势跟踪指标，通过MA的百分比偏移计算止损线。
    
    Attributes:
        period: MA周期
        percent: 止损百分比
        _min_klines_required: 所需的最小K线数量
    
    Example:
        >>> indicator = MAStopIndicator(
        ...     user_id="user_001",
        ...     symbol="XRPUSDC",
        ...     interval="15m",
        ...     indicator_name="ma_stop_ta",
        ...     params={"period": 20, "percent": 2},
        ...     event_bus=event_bus
        ... )
        >>> result = await indicator.calculate(klines)
        >>> print(result)
        {'signal': 'LONG', 'data': {'ma': 1.05, 'stop_line': 1.029, 'close': 1.10}}
    """
    
    def __init__(
        self,
        user_id: str,
        symbol: str,
        interval: str,
        indicator_name: str,
        params: Dict[str, Any],
        event_bus: EventBus
    ):
        """
        初始化MA Stop指标
        
        Args:
            user_id: 用户ID
            symbol: 交易对符号
            interval: 时间周期
            indicator_name: 指标名称
            params: 指标参数
                - period: MA周期（默认20）
                - percent: 止损百分比（默认2）
            event_bus: 事件总线实例
        """
        super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)
        
        # 获取参数
        self.period = params.get("period", 20)
        self.percent = params.get("percent", 2)
        
        # 设置所需的最小K线数量（至少需要period * 2根K线）
        self._min_klines_required = max(self.period * 2, 50)
        
        logger.info(
            f"[ma_stop_indicator.py] "
            f"MA Stop指标初始化: {self._indicator_id}, "
            f"period={self.period}, percent={self.percent}, "
            f"min_klines={self._min_klines_required}"
        )
    
    async def calculate(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算MA Stop指标
        
        计算步骤：
        1. 提取收盘价列表
        2. 计算移动平均线（MA）
        3. 计算止损线（MA * (1 - percent/100) 或 MA * (1 + percent/100)）
        4. 判断信号：
           - 价格 > 上止损线 → LONG
           - 价格 < 下止损线 → SHORT
           - 其他 → NONE
        
        Args:
            klines: 完整的历史K线列表
                每根K线格式：{
                    "open": "1.0",
                    "high": "1.1",
                    "low": "0.9",
                    "close": "1.05",
                    "volume": "1000",
                    "timestamp": 1499040000000,
                    "is_closed": True
                }
        
        Returns:
            指标计算结果：{
                "signal": "LONG" | "SHORT" | "NONE",
                "data": {
                    "ma": 移动平均线值,
                    "stop_line_long": 多头止损线,
                    "stop_line_short": 空头止损线,
                    "close": 最新收盘价,
                    "period": MA周期,
                    "percent": 止损百分比
                }
            }
        """
        try:
            # 1. 提取收盘价列表
            closes = [float(k["close"]) for k in klines]
            
            # 检查K线数量是否足够
            if len(closes) < self.period:
                logger.warning(
                    f"[ma_stop_indicator.py] "
                    f"K线数量不足: {len(closes)} < {self.period}, "
                    f"indicator_id={self._indicator_id}"
                )
                return {
                    "signal": IndicatorSignal.NONE.value,
                    "data": {
                        "error": "K线数量不足",
                        "required": self.period,
                        "actual": len(closes)
                    }
                }
            
            # 2. 计算移动平均线（使用最近period根K线）
            ma_value = sum(closes[-self.period:]) / self.period
            
            # 3. 计算止损线
            # 多头止损线：MA * (1 - percent/100)
            stop_line_long = ma_value * (1 - self.percent / 100)
            # 空头止损线：MA * (1 + percent/100)
            stop_line_short = ma_value * (1 + self.percent / 100)
            
            # 4. 获取最新收盘价
            latest_close = closes[-1]
            
            # 5. 判断信号
            if latest_close > stop_line_long:
                signal = IndicatorSignal.LONG
            elif latest_close < stop_line_short:
                signal = IndicatorSignal.SHORT
            else:
                signal = IndicatorSignal.NONE
            
            # 6. 构造返回结果
            result = {
                "signal": signal.value,
                "data": {
                    "ma": round(ma_value, 6),
                    "stop_line_long": round(stop_line_long, 6),
                    "stop_line_short": round(stop_line_short, 6),
                    "close": round(latest_close, 6),
                    "period": self.period,
                    "percent": self.percent
                }
            }
            
            logger.debug(
                f"[ma_stop_indicator.py] "
                f"MA Stop计算完成: {self._indicator_id}, "
                f"signal={signal.value}, ma={ma_value:.6f}, "
                f"close={latest_close:.6f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"[ma_stop_indicator.py] "
                f"MA Stop计算失败: {self._indicator_id}, error={e}",
                exc_info=True
            )
            return {
                "signal": IndicatorSignal.NONE.value,
                "data": {
                    "error": str(e)
                }
            }

