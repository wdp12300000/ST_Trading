"""
BinanceClient类单元测试

测试BinanceClient类的完整功能，包括：
- 初始化和配置
- API签名生成（HMAC SHA256）
- 请求头构建
- API端点URL验证
- 历史K线获取
- 账户余额查询
- ListenKey管理
"""

import pytest
import time
import hmac
import hashlib
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.core.de.binance_client import BinanceClient


class TestBinanceClientInitialization:
    """测试BinanceClient类的初始化"""
    
    def test_init_with_valid_credentials(self):
        """测试使用有效凭证初始化BinanceClient"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
        
        assert client.user_id == "user_001"
        assert client.api_key == "test_api_key"
        assert client.api_secret == "test_api_secret"
    
    def test_base_url_is_production(self):
        """测试API端点使用币安正式网"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
        
        # 验证使用正式网API端点
        assert client.base_url == "https://fapi.binance.com"
    
    def test_websocket_url_is_production(self):
        """测试WebSocket端点使用币安正式网"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
        
        # 验证使用正式网WebSocket端点
        assert client.ws_url == "wss://fstream.binance.com"


class TestBinanceClientSignature:
    """测试API签名生成"""
    
    def test_generate_signature_with_empty_params(self):
        """测试空参数的签名生成"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_secret"
        )
        
        # 空参数应该生成空字符串的签名
        signature = client._generate_signature("")
        
        # 验证签名是HMAC SHA256的十六进制字符串
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256的十六进制长度
        
        # 验证签名正确性
        expected = hmac.new(
            "test_secret".encode('utf-8'),
            "".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        assert signature == expected
    
    def test_generate_signature_with_params(self):
        """测试带参数的签名生成"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_secret"
        )
        
        # 测试参数字符串
        query_string = "symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=50000&timestamp=1234567890"
        signature = client._generate_signature(query_string)
        
        # 验证签名正确性
        expected = hmac.new(
            "test_secret".encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        assert signature == expected
    
    def test_signature_is_deterministic(self):
        """测试相同输入产生相同签名"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_secret"
        )
        
        query_string = "symbol=BTCUSDT&timestamp=1234567890"
        signature1 = client._generate_signature(query_string)
        signature2 = client._generate_signature(query_string)
        
        assert signature1 == signature2


class TestBinanceClientHeaders:
    """测试请求头构建"""
    
    def test_get_headers_without_signature(self):
        """测试获取不需要签名的请求头"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
        
        headers = client._get_headers()
        
        assert "X-MBX-APIKEY" in headers
        assert headers["X-MBX-APIKEY"] == "test_api_key"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
    
    def test_headers_contain_api_key(self):
        """测试请求头包含API密钥"""
        client = BinanceClient(
            user_id="user_001",
            api_key="my_special_api_key",
            api_secret="test_api_secret"
        )
        
        headers = client._get_headers()
        
        assert headers["X-MBX-APIKEY"] == "my_special_api_key"


class TestBinanceClientQueryString:
    """测试查询字符串构建"""
    
    def test_build_query_string_with_timestamp(self):
        """测试构建带时间戳的查询字符串"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
        
        params = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "limit": 100
        }
        
        query_string = client._build_query_string(params)
        
        # 验证包含所有参数
        assert "symbol=BTCUSDT" in query_string
        assert "interval=1h" in query_string
        assert "limit=100" in query_string
        assert "timestamp=" in query_string
    
    def test_build_query_string_with_signature(self):
        """测试构建带签名的查询字符串"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
        
        params = {"symbol": "BTCUSDT"}
        
        query_string = client._build_query_string(params, sign=True)
        
        # 验证包含签名
        assert "signature=" in query_string
        assert "timestamp=" in query_string


class TestBinanceClientHistoricalKlines:
    """测试历史K线获取（需要mock HTTP请求）"""
    
    @pytest.mark.asyncio
    async def test_get_historical_klines_success(self):
        """测试成功获取历史K线数据"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock响应数据
        mock_response_data = [
            [1640000000000, "50000", "51000", "49000", "50500", "100", 1640003600000, "5000000", 1000, "50", "2500000", "0"],
            [1640003600000, "50500", "52000", "50000", "51500", "120", 1640007200000, "6000000", 1200, "60", "3000000", "0"]
        ]

        # Mock aiohttp session
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法
            klines = await client.get_historical_klines(
                symbol="BTCUSDT",
                interval="1h",
                limit=2
            )

            # 验证返回数据
            assert len(klines) == 2
            assert klines[0][1] == "50000"  # open price
            assert klines[1][1] == "50500"  # open price
    
    @pytest.mark.asyncio
    async def test_get_historical_klines_with_correct_url(self):
        """测试历史K线请求使用正确的URL"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[])
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            await client.get_historical_klines("BTCUSDT", "1h", 100)

            # 验证调用了正确的URL
            call_args = mock_session.get.call_args
            url = call_args[0][0]
            assert url.startswith("https://fapi.binance.com/fapi/v1/klines")
            assert "symbol=BTCUSDT" in url
            assert "interval=1h" in url
            assert "limit=100" in url


class TestBinanceClientAccountBalance:
    """测试账户余额查询"""
    
    @pytest.mark.asyncio
    async def test_get_account_balance_success(self):
        """测试成功查询账户余额"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock响应数据
        mock_response_data = [
            {"asset": "USDT", "balance": "10000.00000000", "availableBalance": "9500.00000000"},
            {"asset": "BTC", "balance": "0.50000000", "availableBalance": "0.45000000"}
        ]

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法
            balance = await client.get_account_balance(asset="USDT")

            # 验证返回数据
            assert balance["asset"] == "USDT"
            assert balance["availableBalance"] == "9500.00000000"


class TestBinanceClientListenKey:
    """测试ListenKey管理"""
    
    @pytest.mark.asyncio
    async def test_create_listen_key_success(self):
        """测试成功创建ListenKey"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock响应数据
        mock_response_data = {"listenKey": "test_listen_key_123456"}

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法
            listen_key = await client.create_listen_key()

            # 验证返回数据
            assert listen_key == "test_listen_key_123456"

    @pytest.mark.asyncio
    async def test_keepalive_listen_key_success(self):
        """测试成功keepalive ListenKey"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.put = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法（应该不抛出异常）
            await client.keepalive_listen_key("test_listen_key")

            # 验证调用了PUT请求
            assert mock_session.put.called


class TestBinanceClientOrderExecution:
    """测试BinanceClient类的订单执行功能"""

    @pytest.mark.asyncio
    async def test_place_order_market_buy(self):
        """测试提交市价买单"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "orderId": 123456789,
                "symbol": "BTCUSDT",
                "status": "NEW",
                "clientOrderId": "test_client_order_id",
                "price": "0",
                "avgPrice": "0.00000",
                "origQty": "0.001",
                "executedQty": "0",
                "cumQty": "0",
                "cumQuote": "0",
                "timeInForce": "GTC",
                "type": "MARKET",
                "reduceOnly": False,
                "closePosition": False,
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "MARKET",
                "updateTime": 1699999999999
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法
            result = await client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001
            )

            # 验证返回结果
            assert result["orderId"] == 123456789
            assert result["symbol"] == "BTCUSDT"
            assert result["side"] == "BUY"
            assert result["type"] == "MARKET"
            assert result["origQty"] == "0.001"

            # 验证调用了POST请求
            assert mock_session.post.called

    @pytest.mark.asyncio
    async def test_place_order_limit_sell(self):
        """测试提交限价卖单"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "orderId": 987654321,
                "symbol": "ETHUSDT",
                "status": "NEW",
                "clientOrderId": "test_client_order_id",
                "price": "2000.00",
                "avgPrice": "0.00000",
                "origQty": "0.1",
                "executedQty": "0",
                "cumQty": "0",
                "cumQuote": "0",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "SELL",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "updateTime": 1699999999999
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法
            result = await client.place_order(
                symbol="ETHUSDT",
                side="SELL",
                order_type="LIMIT",
                quantity=0.1,
                price=2000.00
            )

            # 验证返回结果
            assert result["orderId"] == 987654321
            assert result["symbol"] == "ETHUSDT"
            assert result["side"] == "SELL"
            assert result["type"] == "LIMIT"
            assert result["price"] == "2000.00"
            assert result["origQty"] == "0.1"

            # 验证调用了POST请求
            assert mock_session.post.called

    @pytest.mark.asyncio
    async def test_place_order_api_error(self):
        """测试订单提交API错误"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 模拟错误响应
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value='{"code":-1111,"msg":"Precision is over the maximum defined for this asset."}')
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法应该抛出异常
            with pytest.raises(Exception) as exc_info:
                await client.place_order(
                    symbol="BTCUSDT",
                    side="BUY",
                    order_type="MARKET",
                    quantity=0.001
                )

            # 验证异常信息
            assert "提交订单失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_order_success(self):
        """测试取消订单成功"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "orderId": 123456789,
                "symbol": "BTCUSDT",
                "status": "CANCELED",
                "clientOrderId": "test_client_order_id",
                "price": "50000.00",
                "avgPrice": "0.00000",
                "origQty": "0.001",
                "executedQty": "0",
                "cumQty": "0",
                "cumQuote": "0",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "updateTime": 1699999999999
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.delete = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法
            result = await client.cancel_order(
                symbol="BTCUSDT",
                order_id=123456789
            )

            # 验证返回结果
            assert result["orderId"] == 123456789
            assert result["symbol"] == "BTCUSDT"
            assert result["status"] == "CANCELED"

            # 验证调用了DELETE请求
            assert mock_session.delete.called

    @pytest.mark.asyncio
    async def test_cancel_order_api_error(self):
        """测试取消订单API错误"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 模拟错误响应
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value='{"code":-2011,"msg":"Unknown order sent."}')

            mock_session = MagicMock()
            mock_session.delete = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法应该抛出异常
            with pytest.raises(Exception) as exc_info:
                await client.cancel_order(
                    symbol="BTCUSDT",
                    order_id=999999999
                )

            # 验证异常信息
            assert "取消订单失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_place_order_retry_on_network_error(self):
        """测试订单提交网络错误时自动重试"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 第1-2次失败，第3次成功
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_response_fail.text = AsyncMock(return_value='{"code":-1001,"msg":"Internal error"}')
            mock_response_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
            mock_response_fail.__aexit__ = AsyncMock(return_value=None)

            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.json = AsyncMock(return_value={
                "orderId": 123456789,
                "symbol": "BTCUSDT",
                "status": "NEW",
                "side": "BUY",
                "type": "MARKET",
                "origQty": "0.001"
            })
            mock_response_success.__aenter__ = AsyncMock(return_value=mock_response_success)
            mock_response_success.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            # 前2次返回失败，第3次返回成功
            mock_session.post = MagicMock(side_effect=[
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ])
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法（应该重试后成功）
            result = await client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
                max_retries=3
            )

            # 验证最终成功
            assert result["orderId"] == 123456789

            # 验证调用了3次POST请求
            assert mock_session.post.call_count == 3

    @pytest.mark.asyncio
    async def test_place_order_retry_exhausted(self):
        """测试订单提交重试次数用尽后抛出异常"""
        client = BinanceClient(
            user_id="user_001",
            api_key="test_api_key",
            api_secret="test_api_secret"
        )

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 所有请求都失败
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_response_fail.text = AsyncMock(return_value='{"code":-1001,"msg":"Internal error"}')
            mock_response_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
            mock_response_fail.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response_fail)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # 调用方法应该抛出异常
            with pytest.raises(Exception) as exc_info:
                await client.place_order(
                    symbol="BTCUSDT",
                    side="BUY",
                    order_type="MARKET",
                    quantity=0.001,
                    max_retries=3
                )

            # 验证异常信息
            assert "提交订单失败" in str(exc_info.value)

            # 验证调用了3次POST请求（初始1次 + 重试2次）
            assert mock_session.post.call_count == 3

