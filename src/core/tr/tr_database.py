"""
TR模块数据库

TRDatabase负责TR模块的数据持久化，包括：
1. 交易任务记录
2. 订单记录
3. 利润统计
4. 查询接口

使用方式:
    db = TRDatabase("data/tr_trading.db")
    await db.initialize()
    
    # 保存交易任务
    await db.save_trading_task(task_data)
    
    # 查询历史任务
    tasks = await db.query_trading_tasks(user_id="user_001")
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
import aiosqlite


class TRDatabase:
    """
    TR模块数据库
    
    使用SQLite存储交易任务和订单数据。
    
    Attributes:
        db_path: 数据库文件路径
        _conn: 数据库连接
    """
    
    def __init__(self, db_path: str = "data/tr_trading.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        
        logger.info(f"[tr_database.py:{self._get_line_number()}] TR数据库初始化: {db_path}")
    
    async def initialize(self) -> None:
        """
        初始化数据库连接和表结构
        """
        # 创建数据目录
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 连接数据库
        self._conn = await aiosqlite.connect(self.db_path)
        
        # 创建表
        await self._create_tables()
        
        logger.info(f"[tr_database.py:{self._get_line_number()}] TR数据库初始化完成")
    
    async def _create_tables(self) -> None:
        """创建数据库表"""
        # 交易任务表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trading_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trading_mode TEXT NOT NULL,
                position_state TEXT NOT NULL,
                entry_side TEXT,
                entry_price REAL,
                entry_quantity REAL,
                exit_price REAL,
                total_profit REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                opened_at TEXT,
                closed_at TEXT,
                grid_config TEXT,
                UNIQUE(user_id, symbol, created_at)
            )
        """)
        
        # 订单表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                filled_quantity REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                is_grid_order INTEGER DEFAULT 0,
                grid_pair_id TEXT,
                profit REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                filled_at TEXT,
                FOREIGN KEY (task_id) REFERENCES trading_tasks(id)
            )
        """)
        
        # 利润统计表
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS profit_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                total_profit REAL DEFAULT 0.0,
                profit_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                UNIQUE(user_id, symbol, date)
            )
        """)
        
        await self._conn.commit()
        
        logger.info(f"[tr_database.py:{self._get_line_number()}] 数据库表创建完成")
    
    async def save_trading_task(self, task_data: Dict[str, Any]) -> int:
        """
        保存交易任务
        
        Args:
            task_data: 交易任务数据
        
        Returns:
            int: 任务ID
        """
        cursor = await self._conn.execute("""
            INSERT INTO trading_tasks (
                user_id, symbol, trading_mode, position_state,
                entry_side, entry_price, entry_quantity, exit_price,
                total_profit, created_at, opened_at, closed_at, grid_config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_data.get("user_id"),
            task_data.get("symbol"),
            task_data.get("trading_mode"),
            task_data.get("position_state"),
            task_data.get("entry_side"),
            task_data.get("entry_price"),
            task_data.get("entry_quantity"),
            task_data.get("exit_price"),
            task_data.get("total_profit", 0.0),
            task_data.get("created_at"),
            task_data.get("opened_at"),
            task_data.get("closed_at"),
            json.dumps(task_data.get("grid_config")) if task_data.get("grid_config") else None
        ))
        
        await self._conn.commit()
        task_id = cursor.lastrowid
        
        logger.info(
            f"[tr_database.py:{self._get_line_number()}] 交易任务已保存: "
            f"ID={task_id} {task_data.get('user_id')}/{task_data.get('symbol')}"
        )
        
        return task_id
    
    async def save_order(self, order_data: Dict[str, Any]) -> int:
        """
        保存订单
        
        Args:
            order_data: 订单数据
        
        Returns:
            int: 订单记录ID
        """
        cursor = await self._conn.execute("""
            INSERT INTO orders (
                task_id, order_id, symbol, side, order_type,
                price, quantity, filled_quantity, status,
                is_grid_order, grid_pair_id, profit, created_at, filled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_data.get("task_id"),
            order_data.get("order_id"),
            order_data.get("symbol"),
            order_data.get("side"),
            order_data.get("order_type"),
            order_data.get("price"),
            order_data.get("quantity"),
            order_data.get("filled_quantity", 0.0),
            order_data.get("status"),
            1 if order_data.get("is_grid_order") else 0,
            order_data.get("grid_pair_id"),
            order_data.get("profit", 0.0),
            order_data.get("created_at"),
            order_data.get("filled_at")
        ))
        
        await self._conn.commit()
        order_id = cursor.lastrowid
        
        logger.debug(
            f"[tr_database.py:{self._get_line_number()}] 订单已保存: "
            f"ID={order_id} {order_data.get('order_id')}"
        )
        
        return order_id
    
    async def update_task_profit(self, task_id: int, total_profit: float) -> None:
        """
        更新任务总利润
        
        Args:
            task_id: 任务ID
            total_profit: 总利润
        """
        await self._conn.execute("""
            UPDATE trading_tasks SET total_profit = ? WHERE id = ?
        """, (total_profit, task_id))
        
        await self._conn.commit()
    
    async def query_trading_tasks(
        self,
        user_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询交易任务
        
        Args:
            user_id: 用户ID（可选）
            symbol: 交易对（可选）
            limit: 返回数量限制
        
        Returns:
            List[Dict[str, Any]]: 交易任务列表
        """
        query = "SELECT * FROM trading_tasks WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        
        tasks = []
        for row in rows:
            task = {
                "id": row[0],
                "user_id": row[1],
                "symbol": row[2],
                "trading_mode": row[3],
                "position_state": row[4],
                "entry_side": row[5],
                "entry_price": row[6],
                "entry_quantity": row[7],
                "exit_price": row[8],
                "total_profit": row[9],
                "created_at": row[10],
                "opened_at": row[11],
                "closed_at": row[12],
                "grid_config": json.loads(row[13]) if row[13] else None
            }
            tasks.append(task)
        
        return tasks
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            logger.info(f"[tr_database.py:{self._get_line_number()}] TR数据库连接已关闭")
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

