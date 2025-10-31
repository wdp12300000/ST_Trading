"""
TR数据库单元测试

测试TRDatabase的数据持久化功能。
"""

import pytest
import pytest_asyncio
import os
import tempfile
from datetime import datetime
from src.core.tr.tr_database import TRDatabase


@pytest_asyncio.fixture
async def temp_db():
    """创建临时数据库"""
    # 创建临时文件
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db = TRDatabase(path)
    await db.initialize()
    
    yield db
    
    # 清理
    await db.close()
    if os.path.exists(path):
        os.remove(path)


class TestDatabaseInitialization:
    """测试数据库初始化"""
    
    @pytest.mark.asyncio
    async def test_initialize_database(self, temp_db):
        """测试初始化数据库"""
        assert temp_db is not None
        assert temp_db._conn is not None


class TestTradingTaskPersistence:
    """测试交易任务持久化"""
    
    @pytest.mark.asyncio
    async def test_save_trading_task(self, temp_db):
        """测试保存交易任务"""
        task_data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "trading_mode": "NO_GRID",
            "position_state": "LONG",
            "entry_side": "LONG",
            "entry_price": 1.0,
            "entry_quantity": 100.0,
            "exit_price": 1.05,
            "total_profit": 4.92,
            "created_at": datetime.now().isoformat(),
            "opened_at": datetime.now().isoformat(),
            "closed_at": datetime.now().isoformat(),
            "grid_config": None
        }
        
        task_id = await temp_db.save_trading_task(task_data)
        
        assert task_id > 0
    
    @pytest.mark.asyncio
    async def test_save_trading_task_with_grid_config(self, temp_db):
        """测试保存带网格配置的交易任务"""
        task_data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "trading_mode": "NORMAL_GRID",
            "position_state": "NONE",
            "entry_side": None,
            "entry_price": None,
            "entry_quantity": None,
            "exit_price": None,
            "total_profit": 0.0,
            "created_at": datetime.now().isoformat(),
            "opened_at": None,
            "closed_at": None,
            "grid_config": {
                "upper_price": 1.05,
                "lower_price": 0.95,
                "grid_levels": 10
            }
        }
        
        task_id = await temp_db.save_trading_task(task_data)
        
        assert task_id > 0
    
    @pytest.mark.asyncio
    async def test_query_trading_tasks(self, temp_db):
        """测试查询交易任务"""
        # 保存几个任务
        for i in range(3):
            task_data = {
                "user_id": "user_001",
                "symbol": f"SYMBOL{i}",
                "trading_mode": "NO_GRID",
                "position_state": "NONE",
                "entry_side": None,
                "entry_price": None,
                "entry_quantity": None,
                "exit_price": None,
                "total_profit": 0.0,
                "created_at": datetime.now().isoformat(),
                "opened_at": None,
                "closed_at": None,
                "grid_config": None
            }
            await temp_db.save_trading_task(task_data)
        
        # 查询所有任务
        tasks = await temp_db.query_trading_tasks(user_id="user_001")
        
        assert len(tasks) == 3
    
    @pytest.mark.asyncio
    async def test_query_trading_tasks_by_symbol(self, temp_db):
        """测试按交易对查询"""
        # 保存不同交易对的任务
        for symbol in ["XRPUSDC", "BTCUSDC", "XRPUSDC"]:
            task_data = {
                "user_id": "user_001",
                "symbol": symbol,
                "trading_mode": "NO_GRID",
                "position_state": "NONE",
                "entry_side": None,
                "entry_price": None,
                "entry_quantity": None,
                "exit_price": None,
                "total_profit": 0.0,
                "created_at": datetime.now().isoformat(),
                "opened_at": None,
                "closed_at": None,
                "grid_config": None
            }
            await temp_db.save_trading_task(task_data)
        
        # 查询XRPUSDC
        tasks = await temp_db.query_trading_tasks(user_id="user_001", symbol="XRPUSDC")
        
        assert len(tasks) == 2
        assert all(task["symbol"] == "XRPUSDC" for task in tasks)
    
    @pytest.mark.asyncio
    async def test_update_task_profit(self, temp_db):
        """测试更新任务利润"""
        task_data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "trading_mode": "NO_GRID",
            "position_state": "LONG",
            "entry_side": "LONG",
            "entry_price": 1.0,
            "entry_quantity": 100.0,
            "exit_price": None,
            "total_profit": 0.0,
            "created_at": datetime.now().isoformat(),
            "opened_at": datetime.now().isoformat(),
            "closed_at": None,
            "grid_config": None
        }
        
        task_id = await temp_db.save_trading_task(task_data)
        
        # 更新利润
        await temp_db.update_task_profit(task_id, 10.5)
        
        # 查询验证
        tasks = await temp_db.query_trading_tasks(user_id="user_001")
        assert tasks[0]["total_profit"] == 10.5


class TestOrderPersistence:
    """测试订单持久化"""
    
    @pytest.mark.asyncio
    async def test_save_order(self, temp_db):
        """测试保存订单"""
        # 先创建任务
        task_data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "trading_mode": "NO_GRID",
            "position_state": "NONE",
            "entry_side": None,
            "entry_price": None,
            "entry_quantity": None,
            "exit_price": None,
            "total_profit": 0.0,
            "created_at": datetime.now().isoformat(),
            "opened_at": None,
            "closed_at": None,
            "grid_config": None
        }
        task_id = await temp_db.save_trading_task(task_data)
        
        # 保存订单
        order_data = {
            "task_id": task_id,
            "order_id": "order_123",
            "symbol": "XRPUSDC",
            "side": "BUY",
            "order_type": "MARKET",
            "price": 1.0,
            "quantity": 100.0,
            "filled_quantity": 100.0,
            "status": "FILLED",
            "is_grid_order": False,
            "grid_pair_id": None,
            "profit": 0.0,
            "created_at": datetime.now().isoformat(),
            "filled_at": datetime.now().isoformat()
        }
        
        order_id = await temp_db.save_order(order_data)
        
        assert order_id > 0
    
    @pytest.mark.asyncio
    async def test_save_grid_order(self, temp_db):
        """测试保存网格订单"""
        # 先创建任务
        task_data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "trading_mode": "NORMAL_GRID",
            "position_state": "NONE",
            "entry_side": None,
            "entry_price": None,
            "entry_quantity": None,
            "exit_price": None,
            "total_profit": 0.0,
            "created_at": datetime.now().isoformat(),
            "opened_at": None,
            "closed_at": None,
            "grid_config": None
        }
        task_id = await temp_db.save_trading_task(task_data)
        
        # 保存网格订单
        order_data = {
            "task_id": task_id,
            "order_id": "grid_order_123",
            "symbol": "XRPUSDC",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 0.95,
            "quantity": 10.0,
            "filled_quantity": 10.0,
            "status": "FILLED",
            "is_grid_order": True,
            "grid_pair_id": "pair_001",
            "profit": 0.92,
            "created_at": datetime.now().isoformat(),
            "filled_at": datetime.now().isoformat()
        }
        
        order_id = await temp_db.save_order(order_data)
        
        assert order_id > 0

