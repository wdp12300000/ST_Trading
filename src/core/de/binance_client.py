"""
BinanceClient - 币安REST API客户端

负责与币安永续合约API进行交互，包括：
- API签名生成（HMAC SHA256）
- 历史K线数据获取
- 账户余额查询
- ListenKey管理（用于用户数据流）
- 订单提交和取消

使用方式：
    from src.core.de.binance_client import BinanceClient

    client = BinanceClient(
        user_id="user_001",
        api_key="your_api_key",
        api_secret="your_api_secret"
    )

    # 获取历史K线
    klines = await client.get_historical_klines("BTCUSDT", "1h", 100)

    # 查询账户余额
    balance = await client.get_account_balance("USDT")

    # 创建ListenKey
    listen_key = await client.create_listen_key()
"""

import time
import hmac
import hashlib
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import aiohttp
from src.utils.logger import logger


class BinanceClient:
    """
    币安REST API客户端类

    每个交易账户对应一个BinanceClient实例。
    使用币安正式网API端点，不使用测试网。

    属性：
        user_id: 用户ID
        api_key: 币安API密钥
        api_secret: 币安API密钥（用于签名）
        base_url: REST API基础URL（正式网）
        ws_url: WebSocket基础URL（正式网）
    """

    # 币安正式网API端点
    BASE_URL = "https://fapi.binance.com"
    WS_URL = "wss://fstream.binance.com"

    def __init__(self, user_id: str, api_key: str, api_secret: str):
        """
        初始化BinanceClient实例

        Args:
            user_id: 用户ID
            api_key: 币安API密钥
            api_secret: 币安API密钥

        实现细节：
            - 使用正式网API端点
            - 不记录敏感信息到日志
            - 仅在内存中存储API密钥
        """
        self.user_id = user_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self.BASE_URL
        self.ws_url = self.WS_URL

        # 记录日志（不包含敏感信息）
        logger.info(f"BinanceClient初始化: user_id={user_id}, base_url={self.base_url}")

    def _generate_signature(self, query_string: str) -> str:
        """
        生成API签名（HMAC SHA256）

        Args:
            query_string: 查询字符串（不含signature参数）

        Returns:
            十六进制签名字符串

        实现细节：
            - 使用HMAC SHA256算法
            - 密钥为api_secret
            - 返回十六进制字符串
        """
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _get_headers(self) -> Dict[str, str]:
        """
        构建请求头

        Returns:
            包含API密钥的请求头字典

        实现细节：
            - 包含X-MBX-APIKEY头
            - 包含Content-Type头
        """
        return {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/json"
        }

    def _build_query_string(self, params: Dict[str, Any], sign: bool = False) -> str:
        """
        构建查询字符串

        Args:
            params: 参数字典
            sign: 是否添加签名（默认False）

        Returns:
            查询字符串（如果sign=True则包含signature参数）

        实现细节：
            - 自动添加timestamp参数
            - 如果sign=True，计算并添加signature参数
            - 使用urlencode编码参数
        """
        # 添加时间戳
        params_with_timestamp = params.copy()
        params_with_timestamp['timestamp'] = int(time.time() * 1000)

        # 构建查询字符串
        query_string = urlencode(params_with_timestamp)

        # 如果需要签名
        if sign:
            signature = self._generate_signature(query_string)
            query_string += f"&signature={signature}"

        return query_string

    async def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ) -> List[List]:
        """
        获取历史K线数据

        Args:
            symbol: 交易对（如BTCUSDT）
            interval: K线间隔（如1m, 5m, 1h, 1d）
            limit: 获取数量（默认500，最大1500）

        Returns:
            K线数据列表，每个元素为：
            [
                开盘时间,
                开盘价,
                最高价,
                最低价,
                收盘价,
                成交量,
                收盘时间,
                成交额,
                成交笔数,
                主动买入成交量,
                主动买入成交额,
                忽略
            ]

        Raises:
            Exception: API请求失败
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }

        query_string = self._build_query_string(params, sign=False)
        url = f"{self.base_url}/fapi/v1/klines?{query_string}"

        logger.debug(f"获取历史K线: user_id={self.user_id}, symbol={symbol}, interval={interval}, limit={limit}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"历史K线获取成功: user_id={self.user_id}, symbol={symbol}, count={len(data)}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"历史K线获取失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                    raise Exception(f"获取历史K线失败: {error_text}")

    async def get_account_balance(self, asset: str = "USDT") -> Dict[str, Any]:
        """
        查询账户余额

        Args:
            asset: 资产名称（默认USDT）

        Returns:
            余额信息字典：
            {
                "asset": "USDT",
                "balance": "10000.00000000",
                "availableBalance": "9500.00000000"
            }

        Raises:
            Exception: API请求失败
        """
        params = {}
        query_string = self._build_query_string(params, sign=True)
        url = f"{self.base_url}/fapi/v2/balance?{query_string}"

        logger.debug(f"查询账户余额: user_id={self.user_id}, asset={asset}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    # 查找指定资产
                    for item in data:
                        if item["asset"] == asset:
                            logger.info(f"账户余额查询成功: user_id={self.user_id}, asset={asset}, balance={item['availableBalance']}")
                            return item

                    logger.warning(f"未找到资产: user_id={self.user_id}, asset={asset}")
                    return {"asset": asset, "balance": "0", "availableBalance": "0"}
                else:
                    error_text = await response.text()
                    logger.error(f"账户余额查询失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                    raise Exception(f"查询账户余额失败: {error_text}")

    async def create_listen_key(self) -> str:
        """
        创建用户数据流ListenKey

        Returns:
            ListenKey字符串

        Raises:
            Exception: API请求失败

        实现细节：
            - 使用POST请求
            - 需要API密钥认证
            - ListenKey有效期60分钟
        """
        url = f"{self.base_url}/fapi/v1/listenKey"

        logger.debug(f"创建ListenKey: user_id={self.user_id}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    listen_key = data["listenKey"]
                    logger.info(f"ListenKey创建成功: user_id={self.user_id}")
                    return listen_key
                else:
                    error_text = await response.text()
                    logger.error(f"ListenKey创建失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                    raise Exception(f"创建ListenKey失败: {error_text}")

    async def keepalive_listen_key(self, listen_key: str) -> None:
        """
        延长ListenKey有效期

        Args:
            listen_key: 要延长的ListenKey

        Raises:
            Exception: API请求失败

        实现细节：
            - 使用PUT请求
            - 需要API密钥认证
            - 建议每30分钟调用一次
        """
        url = f"{self.base_url}/fapi/v1/listenKey"
        params = {"listenKey": listen_key}

        logger.debug(f"延长ListenKey: user_id={self.user_id}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self._get_headers(), params=params) as response:
                if response.status == 200:
                    logger.info(f"ListenKey延长成功: user_id={self.user_id}")
                else:
                    error_text = await response.text()
                    logger.error(f"ListenKey延长失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                    raise Exception(f"延长ListenKey失败: {error_text}")

    async def close_listen_key(self, listen_key: str) -> None:
        """
        关闭用户数据流ListenKey

        Args:
            listen_key: 要关闭的ListenKey

        Raises:
            Exception: API请求失败
        """
        url = f"{self.base_url}/fapi/v1/listenKey"
        params = {"listenKey": listen_key}

        logger.debug(f"关闭ListenKey: user_id={self.user_id}")

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self._get_headers(), params=params) as response:
                if response.status == 200:
                    logger.info(f"ListenKey关闭成功: user_id={self.user_id}")
                else:
                    error_text = await response.text()
                    logger.error(f"ListenKey关闭失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                    raise Exception(f"关闭ListenKey失败: {error_text}")

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        close_position: bool = False,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        提交订单到币安

        Args:
            symbol: 交易对（如BTCUSDT）
            side: 订单方向（BUY或SELL）
            order_type: 订单类型（MARKET、LIMIT、STOP、TAKE_PROFIT等）
            quantity: 订单数量
            price: 订单价格（限价单必填）
            time_in_force: 有效方式（GTC、IOC、FOK）
            reduce_only: 是否只减仓
            close_position: 是否触发后全部平仓
            max_retries: 最大重试次数（默认3次）

        Returns:
            订单响应数据，包含orderId、status等字段

        Raises:
            Exception: API请求失败

        实现细节：
            1. 构建订单参数
            2. 添加时间戳和签名
            3. 发送POST请求到/fapi/v1/order
            4. 如果失败且是网络错误（5xx），自动重试
            5. 返回订单响应数据
        """
        url = f"{self.base_url}/fapi/v1/order"

        # 构建订单参数
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity
        }

        # 限价单需要价格和有效方式
        if order_type == "LIMIT":
            if price is None:
                raise ValueError("限价单必须指定价格")
            params["price"] = price
            params["timeInForce"] = time_in_force

        # 可选参数
        if reduce_only:
            params["reduceOnly"] = "true"
        if close_position:
            params["closePosition"] = "true"

        logger.debug(f"提交订单: user_id={self.user_id}, symbol={symbol}, side={side}, type={order_type}, quantity={quantity}")

        # 重试逻辑
        last_error = None
        for attempt in range(max_retries):
            try:
                # 生成签名（每次重试都需要新的时间戳）
                query_string = self._build_query_string(params, sign=True)

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{url}?{query_string}",
                        headers=self._get_headers()
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if attempt > 0:
                                logger.info(f"订单提交成功（重试{attempt}次后）: user_id={self.user_id}, order_id={result.get('orderId')}, symbol={symbol}")
                            else:
                                logger.info(f"订单提交成功: user_id={self.user_id}, order_id={result.get('orderId')}, symbol={symbol}")
                            return result
                        else:
                            error_text = await response.text()
                            # 5xx错误可以重试，4xx错误不重试
                            if response.status >= 500:
                                last_error = Exception(f"提交订单失败: {error_text}")
                                if attempt < max_retries - 1:
                                    logger.warning(f"订单提交失败（尝试{attempt + 1}/{max_retries}）: user_id={self.user_id}, status={response.status}, 将重试")
                                    continue
                            else:
                                # 4xx错误直接抛出，不重试
                                logger.error(f"订单提交失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                                raise Exception(f"提交订单失败: {error_text}")
            except Exception as e:
                if "提交订单失败" in str(e):
                    # 这是我们自己抛出的异常，直接抛出
                    raise
                # 其他异常（如网络异常）也可以重试
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"订单提交异常（尝试{attempt + 1}/{max_retries}）: user_id={self.user_id}, error={e}, 将重试")
                    continue

        # 所有重试都失败
        logger.error(f"订单提交失败（已重试{max_retries}次）: user_id={self.user_id}, symbol={symbol}")
        raise last_error if last_error else Exception("提交订单失败: 未知错误")

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        取消订单

        Args:
            symbol: 交易对（如BTCUSDT）
            order_id: 订单ID（order_id和client_order_id至少提供一个）
            client_order_id: 客户端订单ID

        Returns:
            取消订单响应数据

        Raises:
            Exception: API请求失败
            ValueError: order_id和client_order_id都未提供

        实现细节：
            1. 验证至少提供一个订单标识
            2. 构建取消订单参数
            3. 添加时间戳和签名
            4. 发送DELETE请求到/fapi/v1/order
            5. 返回取消订单响应数据
        """
        if order_id is None and client_order_id is None:
            raise ValueError("必须提供order_id或client_order_id")

        url = f"{self.base_url}/fapi/v1/order"

        # 构建参数
        params = {
            "symbol": symbol
        }

        if order_id is not None:
            params["orderId"] = order_id
        if client_order_id is not None:
            params["origClientOrderId"] = client_order_id

        # 生成签名
        query_string = self._build_query_string(params, sign=True)

        logger.debug(f"取消订单: user_id={self.user_id}, symbol={symbol}, order_id={order_id}")

        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{url}?{query_string}",
                headers=self._get_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"订单取消成功: user_id={self.user_id}, order_id={result.get('orderId')}, symbol={symbol}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"订单取消失败: user_id={self.user_id}, status={response.status}, error={error_text}")
                    raise Exception(f"取消订单失败: {error_text}")

    def __repr__(self) -> str:
        """字符串表示（不包含敏感信息）"""
        return f"BinanceClient(user_id={self.user_id}, base_url={self.base_url})"
