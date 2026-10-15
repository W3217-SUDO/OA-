import tempfile
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.areas.personal_agent.memory_graph import expire_memories, list_memory_audit, run_memory_pipeline


def test_structured_memory_classifies_and_filters_by_owner_and_case():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-") as directory:
        _assert_structured_memory(Path(directory))


def _assert_structured_memory(tmp_path):
    messages = [{"role": "user", "content": f"步骤 {index}"} for index in range(14)]
    result = run_memory_pipeline(
        tmp_path, 7, "a" * 32, None, messages, "请记住，我偏好简洁中文回答"
    )

    item = result["created"]
    assert item["memory_category"] == "preference"
    assert item["source_type"] == "explicit_user"
    assert item["task_scope"] == "global"
    assert item["confidence"] == 0.95
    assert result["summary_metadata"]["memory_category"] == "temporary_state"

    recalled = run_memory_pipeline(
        tmp_path, 7, "b" * 32, None, [], "我的回复偏好是什么"
    )["recalled"]
    assert recalled and recalled[0]["memory_category"] == "preference"
    assert not run_memory_pipeline(
        tmp_path, 8, "b" * 32, None, [], "我的回复偏好是什么"
    )["recalled"]

    case_item = run_memory_pipeline(
        tmp_path, 7, "c" * 32, 99, [], "请记住，案件经验只用于这个案件"
    )["created"]
    assert case_item["memory_category"] == "experience"
    assert case_item["task_scope"] == "case:99"
    assert not run_memory_pipeline(
        tmp_path, 7, "d" * 32, 100, [], "案件经验"
    )["recalled"]


def test_long_term_command_promotes_previous_user_fact():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-command-") as directory:
        _assert_long_term_command(Path(directory))


def _assert_long_term_command(tmp_path):
    result = run_memory_pipeline(
        tmp_path, 7, "e" * 32, None,
        [{"role": "user", "content": "我叫陶威"}],
        "这个要形成长期记忆",
    )
    assert result["created"]["content"] == "我叫陶威"
    assert result["created"]["memory_category"] == "fact"


def test_conflict_replaces_previous_fact_and_writes_audit():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-conflict-") as directory:
        root = Path(directory)
        first = run_memory_pipeline(root, 7, "a" * 32, None, [], "请记住，我叫陶威")["created"]
        second = run_memory_pipeline(root, 7, "b" * 32, None, [], "请记住，我叫李明") ["created"]
        stored = json.loads((root / "memories.json").read_text(encoding="utf-8"))["items"]
        stored_first = next(item for item in stored if item["id"] == first["id"])
        assert stored_first["lifecycle_state"] == "superseded"
        assert stored_first["superseded_by"] == second["id"]
        assert run_memory_pipeline(root, 7, "c" * 32, None, [], "我的名字是什么")["recalled"][0]["content"] == "我叫李明"
        actions = [event["action"] for event in list_memory_audit(root, 7)]
        assert "conflict_resolved" in actions and "created" in actions


def test_expiry_and_case_allowlist_are_enforced():
    with tempfile.TemporaryDirectory(prefix="oa-test-memory-lifecycle-") as directory:
        root = Path(directory)
        result = run_memory_pipeline(root, 7, "a" * 32, 99, [], "请记住，案件经验只用于这个案件", allowed_case_ids=[99])
        item = result["created"]
        assert not run_memory_pipeline(root, 7, "b" * 32, 99, [], "案件经验", allowed_case_ids=[])["recalled"]
        data_path = root / "memories.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        data["settings"]["retention_days"] = 1
        data["items"][0]["updated_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        assert expire_memories(root, 7) == 1
        assert not run_memory_pipeline(root, 7, "c" * 32, 99, [], "案件经验", allowed_case_ids=[99])["recalled"]
        assert any(event["action"] == "expired" and event["memory_id"] == item["id"] for event in list_memory_audit(root, 7))
