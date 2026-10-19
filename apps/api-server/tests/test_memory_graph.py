import tempfile
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.areas.personal_agent.memory_store import expire_memories, list_memory_audit, prepare_memory_context


def test_structured_memory_classifies_and_filters_by_owner_and_case():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-") as directory:
        _assert_structured_memory(Path(directory))


def _assert_structured_memory(tmp_path):
    messages = [{"role": "user", "content": f"步骤 {index}"} for index in range(14)]
    result = prepare_memory_context(
        tmp_path, 7, "a" * 32, None, messages, "请记住，我偏好简洁中文回答"
    )

    item = result["created"]
    assert item["memory_category"] == "preference"
    assert item["source_type"] == "explicit_user"
    assert item["task_scope"] == "global"
    assert item["confidence"] == 0.95
    assert result["summary_metadata"] == {}

    recalled = prepare_memory_context(
        tmp_path, 7, "b" * 32, None, [], "我的回复偏好是什么"
    )["recalled"]
    assert recalled and recalled[0]["memory_category"] == "preference"
    assert not prepare_memory_context(
        tmp_path, 8, "b" * 32, None, [], "我的回复偏好是什么"
    )["recalled"]

    case_item = prepare_memory_context(
        tmp_path, 7, "c" * 32, 99, [], "请记住，案件经验只用于这个案件"
    )["created"]
    assert case_item["memory_category"] == "experience"
    assert case_item["task_scope"] == "case:99"
    assert not prepare_memory_context(
        tmp_path, 7, "d" * 32, 100, [], "案件经验"
    )["recalled"]


def test_long_term_command_promotes_previous_user_fact():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-command-") as directory:
        _assert_long_term_command(Path(directory))


def _assert_long_term_command(tmp_path):
    result = prepare_memory_context(
        tmp_path, 7, "e" * 32, None,
        [{"role": "user", "content": "我叫陶威"}],
        "这个要形成长期记忆",
    )
    assert result["created"]["content"] == "我叫陶威"
    assert result["created"]["memory_category"] == "fact"


def test_conflict_replaces_previous_fact_and_writes_audit():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-conflict-") as directory:
        root = Path(directory)
        first = prepare_memory_context(root, 7, "a" * 32, None, [], "请记住，我叫陶威")["created"]
        second = prepare_memory_context(root, 7, "b" * 32, None, [], "请记住，我叫李明") ["created"]
        stored = json.loads((root / "memories.json").read_text(encoding="utf-8"))["items"]
        stored_first = next(item for item in stored if item["id"] == first["id"])
        assert stored_first["lifecycle_state"] == "superseded"
        assert stored_first["superseded_by"] == second["id"]
        assert prepare_memory_context(root, 7, "c" * 32, None, [], "我的名字是什么")["recalled"][0]["content"] == "我叫李明"
        actions = [event["action"] for event in list_memory_audit(root, 7)]
        assert "conflict_resolved" in actions and "created" in actions


def test_expiry_and_case_allowlist_are_enforced():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-lifecycle-") as directory:
        root = Path(directory)
        result = prepare_memory_context(root, 7, "a" * 32, 99, [], "请记住，案件经验只用于这个案件", allowed_case_ids=[99])
        item = result["created"]
        assert not prepare_memory_context(root, 7, "b" * 32, 99, [], "案件经验", allowed_case_ids=[])["recalled"]
        data_path = root / "memories.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        data["settings"]["retention_days"] = 1
        data["items"][0]["updated_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        assert expire_memories(root, 7) == 1
        assert not prepare_memory_context(root, 7, "c" * 32, 99, [], "案件经验", allowed_case_ids=[99])["recalled"]
        assert any(event["action"] == "expired" and event["memory_id"] == item["id"] for event in list_memory_audit(root, 7))


def test_long_history_is_not_compressed_by_oa_memory_store():
    """长历史保持原样；压缩完全由原生会话处理。"""
    messages = [{"role": "user", "content": "甲" * 2000} for _ in range(20)]
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-dph-only-") as directory:
        result = prepare_memory_context(Path(directory), 7, "dph-only", None, messages, "继续")
    assert result["summary"] == ""
    assert result["summary_metadata"] == {}
    assert len(messages) == 20 and all(len(item["content"]) == 2000 for item in messages)


def test_existing_summary_and_compression_audit_are_preserved_without_recompression():
    """旧摘要及审计记录保留，不再进行第二次压缩。"""
    metadata = {"compressed_at": "2026-10-19T18:00:00+00:00", "compression_count": 3,
                "source_type": "conversation_compression", "covered_message_range": "0-9"}
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-archive-") as directory:
        result = prepare_memory_context(Path(directory), 7, "dph-only", None,
                                        [{"role": "user", "content": "甲" * 20000}], "继续",
                                        "已有历史摘要", summary_metadata=metadata)
    assert result["summary"] == "已有历史摘要"
    assert result["summary_metadata"] == metadata
