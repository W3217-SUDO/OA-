"""个人会话的项目归属，与单轮引用的案件和材料独立。"""

from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ProjectWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["personal", "case"]
    case_id: int | None = Field(default=None, ge=1, strict=True)

    @model_validator(mode="after")
    def validate_case(self):
        if (self.kind == "case") != (self.case_id is not None):
            raise ValueError("案件项目必须指定案件编号，个人项目不能指定案件编号")
        return self


def normalize_workspace(value: Any, *, stored: bool = False) -> dict[str, Any]:
    try:
        return ProjectWorkspace.model_validate(value).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise HTTPException(500 if stored else 422, "项目空间归属格式错误") from exc


def state_workspace(state: dict[str, Any]) -> dict[str, Any]:
    # 旧会话不根据历史引用案件推断项目，也不在读取时迁移文件。
    return normalize_workspace(state.get("workspace", {"kind": "personal"}), stored=True)


def workspace_key(workspace: dict[str, Any]) -> str:
    workspace = normalize_workspace({key: workspace[key] for key in ("kind", "case_id") if key in workspace})
    return "personal" if workspace["kind"] == "personal" else f"case:{workspace['case_id']}"


def require_membership(state: dict[str, Any], workspace: dict[str, Any] | None) -> None:
    if workspace is not None and state_workspace(state) != normalize_workspace(workspace):
        raise HTTPException(409, "对话不属于当前项目空间，请重新选择对话")


async def require_workspace_access(workspace: dict[str, Any], identity, db):
    workspace = normalize_workspace(workspace)
    if workspace["kind"] == "case":
        from app.core.permissions import _ensure_record_module, _require_record_module_menu

        await _require_record_module_menu("case", identity, db, action="查看")
        return await _ensure_record_module(workspace["case_id"], "case", identity, db)


async def require_state_access(state, identity, db, workspace=None) -> None:
    require_membership(state, workspace)
    await require_workspace_access(state_workspace(state), identity, db)


def _case_descriptor(workspace, record, allowed_fields):
    from app.core.system import _record_dict

    # 与普通记录接口共用基础字段投影，不返回案件 data、人员或附件。
    record_view = _record_dict(record, allowed_fields)
    return {**workspace, "title": record_view["title"], "serial_no": record_view["serial_no"]}


async def project_workspace_context(state, identity, db) -> dict[str, Any]:
    workspace = state_workspace(state)
    if workspace["kind"] == "personal":
        return {**workspace, "title": "个人空间"}
    from app.core.system import _allowed_field_keys

    record = await require_workspace_access(workspace, identity, db)
    return _case_descriptor(workspace, record, await _allowed_field_keys(identity, db))


async def workspace_catalog(workspaces, identity, db) -> list[dict[str, Any]]:
    """保留失权项目入口并明确阻断，不读取案件全文或附件。"""
    items = []
    allowed_fields = None
    for workspace in workspaces:
        workspace = normalize_workspace(workspace, stored=True)
        if workspace["kind"] == "personal":
            items.append({**workspace, "title": "个人空间", "available": True})
            continue
        try:
            record = await require_workspace_access(workspace, identity, db)
        except HTTPException as exc:
            if exc.status_code not in (403, 404):
                raise
            items.append({**workspace, "title": "案件空间", "available": False,
                          "unavailable_reason": str(exc.detail)})
        else:
            from app.core.system import _allowed_field_keys

            if allowed_fields is None:
                allowed_fields = await _allowed_field_keys(identity, db)
            items.append({**_case_descriptor(workspace, record, allowed_fields), "available": True})
    return items
