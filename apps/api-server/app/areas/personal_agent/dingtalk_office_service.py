"""个人 Word 的钉钉编辑副本及 OA 新版本回存，元数据沿用私有文件记录。"""

import hashlib
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.config import settings
from app.core.constants import WORD_DOCUMENT_CONTENT_TYPE, logger
from app.core.generated_file_records import FILE_MODULE, actual_user, generated_file_item
from app.core.generated_file_storage import save_generated_file
from app.core.libreoffice_files import validate_docx
from app.data_models.identity import User
from app.data_models.records import BusinessRecord
from app.areas.personal_agent.ai_space_service import space_file_bytes, space_file_record
from app.areas.personal_agent import dingtalk_office_client as office


# DingTalk storage scene values are identifiers, not free-form labels.  Keep
# the scene and its per-user sceneId alphanumeric so the storage API accepts
# the space creation request across enterprise tenants.
SCENE = "oapersonalword"
SESSION_KEY = "dingtalk_office_session"


async def _owner(file_id, identity, db):
    record = await space_file_record(file_id, identity, db)
    user = await actual_user(db, identity)
    data = record.data or {}
    if data.get("owner_user_id") != user.id or data.get("case_id") is not None:
        raise HTTPException(403, "只有文件所属员工可以编辑本人个人空间的 Word")
    if record.status != "available" or not str(data.get("name", "")).lower().endswith(".docx"):
        raise HTTPException(422, "只支持已保存完成的个人 DOCX 文件")
    user_id = str((user.profile or {}).get("dingtalk_user_id") or "").strip()
    if not user_id:
        raise HTTPException(409, "当前 OA 账号尚未绑定钉钉员工账号，请先维护账号绑定")
    duplicate = await db.scalar(select(User.id).where(
        User.id != user.id, User.profile["dingtalk_user_id"].as_string() == user_id,
    ).limit(1))
    if duplicate is not None:
        raise HTTPException(409, "钉钉账号绑定了多个 OA 用户，请先核对真实绑定")
    union_id = await office.member_union_id(user_id)
    binding = {"owner_user_id": user.id, "dingtalk_user_id": user_id, "union_id": union_id,
               "corp_id": settings.dingtalk_corp_id,
               "app_digest": hashlib.sha256(settings.dingtalk_app_key.encode()).hexdigest()}
    return record.id, binding


async def _locked(db, record_id):
    record = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == record_id)
                             .with_for_update().execution_options(populate_existing=True))
    if record is None or record.status != "available":
        raise HTTPException(409, "原 Word 文件已不可用，编辑未继续")
    return record


def _session(record, binding, session_id=None):
    session = (record.data or {}).get(SESSION_KEY)
    if not isinstance(session, dict) or any(session.get(key) != value for key, value in binding.items()):
        raise HTTPException(409, "钉钉编辑记录与当前员工或企业应用不一致")
    if session_id is not None and session.get("id") != session_id:
        raise HTTPException(409, "钉钉编辑记录已变化，请重新打开当前文件")
    if session.get("source_sha256") != record.data.get("sha256"):
        raise HTTPException(409, "原文件摘要已变化，禁止沿用旧编辑副本")
    return session


async def _store(db, record, session):
    record.data = {**record.data, SESSION_KEY: session}
    await db.commit()


def _validate_space(space, binding, scene_id):
    if (not isinstance(space, dict) or space.get("ownerType") != "USER"
            or space.get("creatorId") != binding["union_id"] or space.get("corpId") != binding["corp_id"]
            or space.get("scene") != SCENE or space.get("sceneId") != scene_id or space.get("status") != "NORMAL"):
        raise HTTPException(409, "钉钉空间的用户、企业或业务归属不一致")
    office.identifier(space.get("id"))
    office.identifier(space.get("ownerId"))


async def _check_space(session):
    result = await office.storage_request("GET", "spaces/" + office.identifier(session["space_id"]), session["union_id"])
    space = result.get("space")
    _validate_space(space, session, session["scene_id"])
    if space["id"] != session["space_id"] or space.get("ownerId") != session["space_owner_id"]:
        raise HTTPException(409, "钉钉空间归属已变化，未继续文件操作")


async def _uncertain(db, record_id, session_id, phase, binding, error):
    try:
        await db.rollback()
        # 失败审计允许锁定墓碑，只修改原会话状态，不恢复文件或删除计划。
        record = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.id == record_id, BusinessRecord.module == FILE_MODULE,
        ).with_for_update().execution_options(populate_existing=True))
        if record is None:
            raise HTTPException(409, "原 Word 元记录不存在，失败审计未完成")
        session = (record.data or {}).get(SESSION_KEY)
        if isinstance(session, dict) and session.get("id") == session_id and session.get("phase") == phase:
            if record.data.get("owner_user_id") != binding["owner_user_id"] or record.data.get("case_id") is not None:
                raise HTTPException(409, "原 Word 归属已变化，失败审计未更新")
            session = _session(record, binding, session_id)
            await _store(db, record, {**session, "phase": "uncertain"})
    except Exception as audit_error:
        # 审计失败必须记录，但不能遮蔽 writer 的 file_id/status 或取消、未知异常。
        error.add_note(f"钉钉编辑失败审计未完成（{type(audit_error).__name__}），请核对原会话与文件保存计划")
        logger.exception("钉钉编辑失败审计未完成，文件记录=%s，会话=%s", record_id, session_id)


async def start_office_edit(file_id, expected_sha256, identity, db):
    record_id, binding = await _owner(file_id, identity, db)
    item, content = await space_file_bytes(file_id, identity, db)
    if item["sha256"] != expected_sha256:
        raise HTTPException(409, "文件版本已变化，请重新核对后打开钉钉编辑")
    validate_docx(content)
    record = await _locked(db, record_id)
    session = (record.data or {}).get(SESSION_KEY)
    if session is not None:
        session = _session(record, binding)
        if session.get("phase") != "ready":
            raise HTTPException(409, "先前钉钉操作正在进行或结果未确认，禁止重复上传，请人工核对")
        await db.commit()
        await _check_space(session)
        return {"session_id": session["id"], "url": await office.editor_url(session), "name": item["name"]}
    session_id = uuid4().hex
    scene_id = f"personal{binding['owner_user_id']}{binding['app_digest'][:16]}"
    session = {**binding, "id": session_id, "phase": "copying", "source_sha256": expected_sha256,
               "scene_id": scene_id, "source_name": item["name"]}
    # 外部写入前持久登记，断网或进程中断后不自动重放非幂等文件提交。
    await _store(db, record, session)
    try:
        result = await office.storage_request("POST", "spaces", binding["union_id"], {
            "option": {"name": "OA个人Word编辑", "ownerType": "USER", "scene": SCENE, "sceneId": scene_id},
        })
        space = result.get("space")
        _validate_space(space, binding, scene_id)
        session = {**session, "space_id": space["id"], "space_owner_id": space.get("ownerId")}
        record = await _locked(db, record_id)
        await _store(db, record, session)
        remote_name = item["name"][:-5][:150] + "-" + session_id + ".docx"
        dentry = await office.upload_copy(space["id"], binding["union_id"], remote_name, content)
        office.identifier(dentry.get("id"))
        session = {**session, "dentry_id": dentry["id"]}
        record = await _locked(db, record_id)
        await _store(db, record, session)
        checked = await office.dentry_info(session)
        copied = await office.download_version(session, checked["version"])
        if hashlib.sha256(copied).hexdigest() != expected_sha256:
            raise HTTPException(409, "钉钉副本回读摘要不一致，原 Word 未修改")
        session = {**session, "phase": "ready", "copied_version": checked["version"]}
        record = await _locked(db, record_id)
        await _store(db, record, session)
    except BaseException as error:
        await _uncertain(db, record_id, session_id, "copying", binding, error)
        raise
    return {"session_id": session_id, "url": await office.editor_url(session), "name": item["name"]}


async def save_office_edit(file_id, session_id, identity, db):
    record_id, binding = await _owner(file_id, identity, db)
    record = await _locked(db, record_id)
    session = _session(record, binding, session_id)
    if session.get("phase") != "ready":
        raise HTTPException(409, "钉钉回存正在进行或结果未确认，请核对状态，禁止重复回存")
    await _check_space(session)
    dentry = await office.dentry_info(session)
    version = dentry["version"]
    if version == session.get("saved_version"):
        saved = await space_file_record(session["result_file_id"], identity, db)
        if saved.status != "available":
            raise HTTPException(409, "该版本的 OA 文件尚不可用，请核对保存状态")
        return {"file": generated_file_item(saved, requesting_user_id=binding["owner_user_id"]),
                "supersedes": file_id, "unchanged": True}
    content = await office.download_version(session, version)
    if len(content) != dentry["size"]:
        raise HTTPException(409, "钉钉文件大小与版本信息不一致，未保存回 OA")
    digest = validate_docx(content)
    if digest == session["source_sha256"]:
        raise HTTPException(409, "钉钉副本尚无内容修改，请先在钉钉完成编辑并保存")
    after = await office.dentry_info(session)
    if after["version"] != version:
        raise HTTPException(409, "钉钉文件仍在保存，请稍后重新取回已保存版本")
    record = await _locked(db, record_id)
    current = _session(record, binding, session_id)
    if current.get("phase") != "ready" or current.get("saved_version") != session.get("saved_version"):
        raise HTTPException(409, "另一个回存操作已更新此文件，请刷新后核对")
    await _store(db, record, {**current, "phase": "saving", "saving_version": version})

    async def link_result(active_db, attachment):
        source = await _locked(active_db, record_id)
        if (source.data.get("file_id") != file_id or source.data.get("owner_user_id") != binding["owner_user_id"]
                or source.data.get("case_id") is not None):
            raise HTTPException(409, "原 Word 的个人归属已变化，未确认新版本")
        active = _session(source, binding, session_id)
        if active.get("phase") != "saving" or active.get("saving_version") != version:
            raise HTTPException(409, "编辑回存记录已变化，未确认新版本")
        result = await active_db.get(BusinessRecord, attachment.record_id)
        if (result is None or result.module != FILE_MODULE or result.status != "available"
                or result.data.get("owner_user_id") != binding["owner_user_id"] or result.data.get("case_id") is not None
                or result.data.get("sha256") != digest or result.data.get("source_kind") != "dingtalk_office_edit"
                or result.data.get("source_request_id") != session_id or result.data.get("attachment_id") != attachment.id):
            raise HTTPException(409, "新 Word 文件关联不完整，未确认回存")
        result.data = {**result.data, "supersedes": file_id}
        source.data = {**source.data, SESSION_KEY: {**active, "phase": "ready", "saved_version": version,
                                                  "result_file_id": result.data["file_id"]}}

    try:
        result = await save_generated_file(db, identity, name=session["source_name"], content=content,
                                          content_type=WORD_DOCUMENT_CONTENT_TYPE, source_kind="dingtalk_office_edit",
                                          conversation_id=record.data.get("conversation_id"),
                                          source_request_id=session_id, on_available=link_result)
    except BaseException as error:
        await _uncertain(db, record_id, session_id, "saving", binding, error)
        raise
    saved = await space_file_record(result["file"]["id"], identity, db)
    return {"file": generated_file_item(saved, requesting_user_id=binding["owner_user_id"]),
            "supersedes": file_id, "unchanged": False}
