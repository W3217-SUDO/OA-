from fastapi.testclient import TestClient

from app.main import OFFICIAL_DOCUMENT_STATUS_NAMES, OFFICIAL_DOCUMENT_TYPE_NAMES, app


def test_official_document_statuses_match_captured_legacy_select_values() -> None:
    assert OFFICIAL_DOCUMENT_STATUS_NAMES == {
        10: "待审核",
        20: "已审待用印",
        30: "审核拒绝",
        40: "已撤回",
        60: "已用印",
    }
    assert OFFICIAL_DOCUMENT_TYPE_NAMES == {10: "合同用印", 20: "案件用印", 30: "行政用印"}


def test_official_document_list_uses_legacy_response_envelope_and_paging() -> None:
    response = TestClient(app).get("/api/v1/legacy/official-documents", params={"page_no": 1, "page_size": 15})
    assert response.status_code == 200
    payload = response.json()
    assert payload["IsSuccess"] is True
    assert payload["Data"]["PageNo"] == 1
    assert payload["Data"]["PageSize"] == 15
    assert isinstance(payload["Data"]["TotalItemCount"], int)
    assert isinstance(payload["Data"]["OfficialDocuments"], list)
