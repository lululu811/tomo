"""Tests for the memory and affinity system."""



from tomo.memory_manager import (
    AFFINITY_GAINS,
    MemoryManager,
)


class TestAffinity:
    def test_get_affinity_default(self, temp_db):
        mgr = MemoryManager(temp_db)
        assert mgr.get_affinity() == 0

    def test_add_affinity_chat(self, temp_db):
        mgr = MemoryManager(temp_db)
        level = mgr.add_affinity("chat")
        assert level.score == AFFINITY_GAINS["chat"]
        assert mgr.get_affinity() == AFFINITY_GAINS["chat"]

    def test_add_affinity_multiple(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.add_affinity("chat")
        mgr.add_affinity("feed")
        expected = AFFINITY_GAINS["chat"] + AFFINITY_GAINS["feed"]
        assert mgr.get_affinity() == expected

    def test_affinity_level_progression(self, temp_db):
        mgr = MemoryManager(temp_db)
        # Add enough to reach "认识" (threshold 10)
        for _ in range(10):
            mgr.add_affinity("chat")
        level = mgr._get_affinity_level(mgr.get_affinity())
        assert level.title == "认识"
        assert level.next_title == "朋友"

    def test_affinity_level_max(self, temp_db):
        mgr = MemoryManager(temp_db)
        for _ in range(600):
            mgr.add_affinity("chat")
        level = mgr._get_affinity_level(mgr.get_affinity())
        assert level.title == "灵魂伴侣"
        assert level.next_title is None
        assert level.progress == 1.0

    def test_affinity_display(self, temp_db):
        mgr = MemoryManager(temp_db)
        display = mgr.get_affinity_display()
        assert "亲密度" in display
        assert "陌生人" in display


class TestMemoryCRUD:
    def test_remember_and_recall(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("coffee", "用户喜欢美式咖啡", "preference")
        assert mgr.recall("coffee") == "用户喜欢美式咖啡"

    def test_recall_missing(self, temp_db):
        mgr = MemoryManager(temp_db)
        assert mgr.recall("nonexistent") is None

    def test_forget(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("temp", "temporary", "fact")
        assert mgr.forget("temp") is True
        assert mgr.recall("temp") is None

    def test_forget_missing(self, temp_db):
        mgr = MemoryManager(temp_db)
        assert mgr.forget("nonexistent") is True  # Already gone

    def test_list_memories(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("a", "value a", "fact")
        mgr.remember("b", "value b", "preference")
        memories = mgr.list_memories()
        assert len(memories) == 2

    def test_list_by_category(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("a", "value a", "fact")
        mgr.remember("b", "value b", "preference")
        facts = mgr.list_memories(category="fact")
        assert len(facts) == 1
        assert facts[0]["value"] == "value a"

    def test_search_memories(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("coffee", "喜欢美式", "preference")
        mgr.remember("tea", "喜欢绿茶", "preference")
        results = mgr.search("美式")
        assert len(results) == 1
        assert results[0]["key"] == "coffee"

    def test_clear_memories(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("a", "value", "fact")
        mgr.clear()
        assert mgr.list_memories() == []

    def test_update_existing_memory(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("key1", "old value", "fact")
        mgr.remember("key1", "new value", "fact")
        assert mgr.recall("key1") == "new value"


class TestAutoExtraction:
    def test_extract_deadline(self, temp_db):
        mgr = MemoryManager(temp_db)
        msg = "明天要发布v2.0了"
        extracted = mgr.extract_from_message(msg)
        assert len(extracted) >= 1
        assert extracted[0][0] == "deadline"

    def test_extract_preference(self, temp_db):
        mgr = MemoryManager(temp_db)
        msg = "我讨厌写CSS"
        extracted = mgr.extract_from_message(msg)
        assert any(e[0] == "preference" for e in extracted)

    def test_extract_goal(self, temp_db):
        mgr = MemoryManager(temp_db)
        msg = "我要学完Rust"
        extracted = mgr.extract_from_message(msg)
        assert any(e[0] == "goal" for e in extracted)

    def test_extract_stress(self, temp_db):
        mgr = MemoryManager(temp_db)
        msg = "最近压力好大"
        extracted = mgr.extract_from_message(msg)
        assert any(e[0] == "stress" for e in extracted)

    def test_extract_nothing(self, temp_db):
        mgr = MemoryManager(temp_db)
        msg = "你好"
        extracted = mgr.extract_from_message(msg)
        assert extracted == []

    def test_store_extracted(self, temp_db):
        mgr = MemoryManager(temp_db)
        msg = "明天要发布"
        stored = mgr.store_extracted(msg)
        assert len(stored) >= 1
        # Second store should not duplicate
        stored2 = mgr.store_extracted(msg)
        assert len(stored2) == 0


class TestMemoryContext:
    def test_get_memory_context(self, temp_db):
        mgr = MemoryManager(temp_db)
        mgr.remember("c1", "喜欢咖啡", "preference")
        mgr.remember("c2", "明天发布", "deadline")
        lines = mgr.get_memory_context(limit=5)
        assert len(lines) == 2
        assert any("喜好" in line for line in lines)
        assert any("deadline" in line for line in lines)

    def test_get_memory_context_empty(self, temp_db):
        mgr = MemoryManager(temp_db)
        lines = mgr.get_memory_context()
        assert lines == []
