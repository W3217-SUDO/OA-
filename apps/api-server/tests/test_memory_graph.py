import tempfile
from pathlib import Path

from app.areas.personal_agent.memory_graph import run_memory_pipeline


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
