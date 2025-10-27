"""
AbstractEventStore 抽象接口测试

测试抽象接口的定义和具体实现的符合性
"""

import pytest
from abc import ABC
from src.core.abstract_event_store import AbstractEventStore
from src.core.event import Event


class TestAbstractEventStore:
    """AbstractEventStore 抽象接口测试"""
    
    def test_abstract_event_store_is_abstract(self):
        """测试 AbstractEventStore 是抽象类"""
        assert issubclass(AbstractEventStore, ABC), "AbstractEventStore 应该继承自 ABC"
    
    def test_cannot_instantiate_abstract_event_store(self):
        """测试不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            AbstractEventStore()
    
    def test_abstract_methods_defined(self):
        """测试所有抽象方法都已定义"""
        abstract_methods = AbstractEventStore.__abstractmethods__
        
        expected_methods = {
            'insert_event',
            'query_recent_events',
            'query_events_by_subject',
            'cleanup_old_events',
            'close'
        }
        
        assert abstract_methods == expected_methods, "应该定义所有必需的抽象方法"
    
    def test_concrete_implementation_must_implement_all_methods(self):
        """测试具体实现必须实现所有抽象方法"""
        
        # 不完整的实现（缺少方法）
        class IncompleteStore(AbstractEventStore):
            def insert_event(self, event):
                pass
        
        # 应该无法实例化
        with pytest.raises(TypeError):
            IncompleteStore()
    
    def test_concrete_implementation_can_be_instantiated(self):
        """测试完整实现可以被实例化"""
        
        # 完整的实现
        class CompleteStore(AbstractEventStore):
            def insert_event(self, event):
                pass
            
            def query_recent_events(self, limit=100):
                return []
            
            def query_events_by_subject(self, subject, limit=100):
                return []
            
            def cleanup_old_events(self):
                pass
            
            def close(self):
                pass
        
        # 应该可以实例化
        store = CompleteStore()
        assert isinstance(store, AbstractEventStore), "应该是 AbstractEventStore 的实例"


class TestSQLiteEventStoreInterface:
    """测试 SQLiteEventStore 是否符合抽象接口"""
    
    def test_sqlite_event_store_implements_interface(self):
        """测试 SQLiteEventStore 实现了 AbstractEventStore 接口"""
        from src.core.event_store import SQLiteEventStore
        
        assert issubclass(SQLiteEventStore, AbstractEventStore), \
            "SQLiteEventStore 应该继承自 AbstractEventStore"
    
    def test_sqlite_event_store_can_be_instantiated(self, tmp_path):
        """测试 SQLiteEventStore 可以被实例化"""
        from src.core.event_store import SQLiteEventStore
        
        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))
        
        assert isinstance(store, AbstractEventStore), \
            "SQLiteEventStore 实例应该是 AbstractEventStore 类型"
        
        store.close()
    
    def test_sqlite_event_store_has_all_methods(self, tmp_path):
        """测试 SQLiteEventStore 实现了所有必需的方法"""
        from src.core.event_store import SQLiteEventStore
        
        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))
        
        # 检查所有方法都存在且可调用
        assert callable(store.insert_event), "insert_event 应该是可调用的"
        assert callable(store.query_recent_events), "query_recent_events 应该是可调用的"
        assert callable(store.query_events_by_subject), "query_events_by_subject 应该是可调用的"
        assert callable(store.cleanup_old_events), "cleanup_old_events 应该是可调用的"
        assert callable(store.close), "close 应该是可调用的"
        
        store.close()


class TestDependencyInjection:
    """测试依赖注入功能"""
    
    def test_can_use_different_implementations(self, tmp_path):
        """测试可以使用不同的存储实现"""
        from src.core.event_store import SQLiteEventStore
        
        # 创建两个不同的实现
        db_path1 = tmp_path / "db1.db"
        db_path2 = tmp_path / "db2.db"
        
        store1 = SQLiteEventStore(db_path=str(db_path1))
        store2 = SQLiteEventStore(db_path=str(db_path2))
        
        # 两个实例应该是独立的
        assert store1 is not store2, "应该是不同的实例"
        assert store1.db_path != store2.db_path, "应该使用不同的数据库"
        
        store1.close()
        store2.close()
    
    def test_mock_implementation_for_testing(self):
        """测试可以使用 Mock 实现进行测试"""
        
        # 创建一个 Mock 实现用于测试
        class MockEventStore(AbstractEventStore):
            def __init__(self):
                self.events = []
            
            def insert_event(self, event):
                self.events.append(event)
            
            def query_recent_events(self, limit=100):
                return [e.to_dict() for e in self.events[-limit:]]
            
            def query_events_by_subject(self, subject, limit=100):
                filtered = [e for e in self.events if e.subject == subject]
                return [e.to_dict() for e in filtered[-limit:]]
            
            def cleanup_old_events(self):
                self.events = self.events[-1000:]
            
            def close(self):
                pass
        
        # 使用 Mock 实现
        mock_store = MockEventStore()
        
        # 插入事件
        event = Event(subject="test", data={"key": "value"})
        mock_store.insert_event(event)
        
        # 查询事件
        recent = mock_store.query_recent_events()
        assert len(recent) == 1, "应该有一个事件"
        assert recent[0]["subject"] == "test", "应该是正确的事件"
        
        mock_store.close()
    
    def test_function_accepts_abstract_type(self, tmp_path):
        """测试函数可以接受抽象类型参数"""
        from src.core.event_store import SQLiteEventStore
        
        def process_events(store: AbstractEventStore):
            """接受抽象类型的函数"""
            event = Event(subject="test", data={})
            store.insert_event(event)
            return store.query_recent_events(limit=1)
        
        # 使用具体实现
        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))
        
        result = process_events(store)
        assert len(result) == 1, "应该返回一个事件"
        
        store.close()

