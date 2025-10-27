"""
EventStore 事件持久化层

使用 SQLite3 实现事件的持久化存储，包括：
- 数据库初始化和表结构创建
- 事件插入
- 历史事件查询
- 自动清理机制（保留最近1000条记录）
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.event import Event
from src.utils.logger import get_logger

logger = get_logger()


class EventStore:
    """
    事件持久化存储类
    
    使用 SQLite3 数据库存储事件，提供事件的插入、查询和自动清理功能
    
    Attributes:
        db_path: 数据库文件路径
        conn: 数据库连接对象
        max_events: 最大保留事件数量，默认1000条
    
    使用方式：
        store = EventStore(db_path="data/events.db")
        store.insert_event(event)
        events = store.query_recent_events(limit=10)
        store.close()
    """
    
    def __init__(self, db_path: str = "data/events.db", max_events: int = 1000):
        """
        初始化事件存储
        
        Args:
            db_path: 数据库文件路径
            max_events: 最大保留事件数量
        
        实现细节：
            - 创建数据库文件所在目录（如果不存在）
            - 建立数据库连接
            - 创建 events 表（如果不存在）
        """
        self.db_path = db_path
        self.max_events = max_events
        
        # 确保数据库目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # 建立数据库连接
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        
        # 创建表结构
        self._create_table()
        
        logger.info(f"事件存储初始化完成: {db_path}")
    
    def _create_table(self):
        """
        创建 events 表
        
        表结构：
            - id: 自增主键
            - event_id: 事件唯一标识符（UUID）
            - subject: 事件主题
            - data: 事件数据（JSON格式）
            - timestamp: 事件时间戳
            - source: 事件源模块
            - created_at: 记录创建时间
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引以提高查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subject ON events(subject)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
        """)
        
        self.conn.commit()
        logger.debug("events 表结构创建完成")
    
    def insert_event(self, event: Event):
        """
        插入事件到数据库
        
        Args:
            event: Event 对象
        
        实现细节：
            - 将事件数据序列化为JSON
            - 插入到数据库
            - 检查记录数量，超过最大值时自动清理
        """
        cursor = self.conn.cursor()
        
        # 将 data 字典序列化为 JSON 字符串
        data_json = json.dumps(event.data, ensure_ascii=False)
        
        # 将 timestamp 转换为 ISO 格式字符串
        timestamp_str = event.timestamp.isoformat()
        
        cursor.execute("""
            INSERT INTO events (event_id, subject, data, timestamp, source)
            VALUES (?, ?, ?, ?, ?)
        """, (event.event_id, event.subject, data_json, timestamp_str, event.source))
        
        self.conn.commit()
        
        logger.debug(f"事件已插入: {event.subject} (ID: {event.event_id})")
        
        # 检查是否需要清理旧事件
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        
        if count > self.max_events:
            self.cleanup_old_events()
    
    def query_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        查询最近的事件
        
        Args:
            limit: 返回的最大事件数量
        
        Returns:
            事件列表，按时间倒序排列（最新的在前）
        
        实现细节：
            - 按 id 倒序排列（最新的记录 id 最大）
            - 反序列化 JSON 数据
            - 转换时间戳为 datetime 对象
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT event_id, subject, data, timestamp, source
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            event_dict = {
                "event_id": row["event_id"],
                "subject": row["subject"],
                "data": json.loads(row["data"]),
                "timestamp": datetime.fromisoformat(row["timestamp"]),
                "source": row["source"]
            }
            events.append(event_dict)
        
        logger.debug(f"查询到 {len(events)} 条最近事件")
        return events
    
    def query_events_by_subject(self, subject: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        按主题查询事件
        
        Args:
            subject: 事件主题
            limit: 返回的最大事件数量
        
        Returns:
            匹配主题的事件列表，按时间倒序排列
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT event_id, subject, data, timestamp, source
            FROM events
            WHERE subject = ?
            ORDER BY id DESC
            LIMIT ?
        """, (subject, limit))
        
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            event_dict = {
                "event_id": row["event_id"],
                "subject": row["subject"],
                "data": json.loads(row["data"]),
                "timestamp": datetime.fromisoformat(row["timestamp"]),
                "source": row["source"]
            }
            events.append(event_dict)
        
        logger.debug(f"查询到 {len(events)} 条主题为 '{subject}' 的事件")
        return events
    
    def cleanup_old_events(self):
        """
        清理旧事件，保留最近的 max_events 条记录
        
        实现细节：
            - 删除 id 最小的记录（最旧的记录）
            - 保留 id 最大的 max_events 条记录（最新的记录）
        """
        cursor = self.conn.cursor()
        
        # 获取当前记录数
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        
        if count <= self.max_events:
            logger.debug(f"当前事件数 {count}，无需清理")
            return
        
        # 计算需要删除的记录数
        to_delete = count - self.max_events
        
        # 删除最旧的记录
        cursor.execute("""
            DELETE FROM events
            WHERE id IN (
                SELECT id FROM events
                ORDER BY id ASC
                LIMIT ?
            )
        """, (to_delete,))
        
        self.conn.commit()
        
        logger.info(f"清理了 {to_delete} 条旧事件，保留最近 {self.max_events} 条")
    
    def close(self):
        """
        关闭数据库连接
        
        实现细节：
            - 提交未完成的事务
            - 关闭数据库连接
        """
        if self.conn:
            self.conn.commit()
            self.conn.close()
            logger.info("事件存储连接已关闭")

