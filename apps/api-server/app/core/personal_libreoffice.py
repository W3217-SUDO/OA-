"""Owner-scoped personal DOCX sessions, independent of case write authority."""
import copy
import re
import secrets
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select, update

from app.config import settings
from app.core.constants import AI_SPACE_CATEGORY
from app.core.generated_file_records import FILE_MODULE, SPACE_MODULE, generated_storage_config, generated_storage_endpoint
from app.core.libreoffice_config import discovery, editor_configuration, editor_url, origin
from app.core.libreoffice_files import read_document, validate_docx
from app.core.libreoffice_security import fresh_identity, session_token
from app.core.libreoffice_state import OfficeContext, iso_utc, now_utc, persist_context, require_lease, status_payload, store_session
from app.core.oss_attachments import oss_attachment_location
from app.core.permissions import _ensure_case_word_editor_not_locked, _ensure_record_module
from app.models import BusinessRecord, FileAttachment, User


def personal_metadata(data):
    if (not isinstance(data, dict)
            or any(type(data.get(key)) is not int or data[key] <= 0 for key in ('owner_user_id', 'space_id', 'attachment_id'))
            or (data.get('case_id') is not None and (type(data['case_id']) is not int or data['case_id'] <= 0))
            or any(not isinstance(data.get(key), str) or not data[key] for key in ('name', 'stored_name', 'path'))
            or type(data.get('size')) is not int or data['size'] <= 0
            or (data.get('versions') is not None and not isinstance(data['versions'], list))
            or (data.get('libreoffice_sessions') is not None and not isinstance(data['libreoffice_sessions'], dict))):
        raise HTTPException(409, '个人文件所有者或关联元数据不完整')
    return data


async def personal_attachment_context(file_id, identity, db, *, lock=False):
    editor_configuration(personal=True)
    identity = await fresh_identity(identity['username'], db)
    user = await db.scalar(select(User).where(User.username == identity['username']))
    if user is None:
        raise HTTPException(401, '当前账号已不存在')
    query = select(BusinessRecord).where(
        BusinessRecord.module == FILE_MODULE, BusinessRecord.serial_no == 'AIGF-' + file_id,
    ).execution_options(populate_existing=True)
    record = await db.scalar(query.with_for_update() if lock else query)
    if record is None:
        raise HTTPException(404, '个人文件不存在')
    data = personal_metadata(record.data)
    if data.get('owner_user_id') != user.id and 'admin' not in identity['role_ids']:
        raise HTTPException(403, '无权编辑其他员工的个人文件')
    owner = await db.get(User, data['owner_user_id'])
    if owner is None or record.owner != owner.username:
        raise HTTPException(409, '个人文件所有者与真实账号绑定不一致')
    if record.status != 'available' or data.get('file_id') != file_id or not str(data.get('name', '')).lower().endswith('.docx'):
        raise HTTPException(409, '仅能编辑已完成保存的 DOCX 文件')
    if data['size'] > settings.office_editor_max_file_bytes:
        raise HTTPException(413, 'DOCX 超过在线编辑大小限制')
    if data.get('case_id') is not None:
        await _ensure_record_module(data['case_id'], 'case', identity, db)
    query = select(FileAttachment).where(FileAttachment.id == data.get('attachment_id')).execution_options(populate_existing=True)
    item = await db.scalar(query.with_for_update() if lock else query)
    if item is None:
        raise HTTPException(404, '个人文件附件不存在')
    # A migrated case attachment may only become a separate personal reference;
    # it must never be mutated via this personal route.
    if (item.record_id != record.id and (data.get('case_id') is None or item.record_id != data['case_id'])):
        raise HTTPException(409, '迁移文件附件归属不完整，请先核对真实关联')
    expected_category = '个人AI空间' if item.record_id == record.id else AI_SPACE_CATEGORY
    if item.category != expected_category:
        raise HTTPException(409, '个人文件附件类别不一致')
    if (item.path != data.get('path') or item.size != data.get('size') or item.is_locked
            or item.original_name != data['name'] or item.stored_name != data['stored_name']
            or (item.record_id == record.id and item.uploader != owner.username)):
        raise HTTPException(409, '文件与附件当前版本不一致或已锁定')
    bucket, prefix = generated_storage_config()
    endpoint = generated_storage_endpoint()
    location = oss_attachment_location(item)
    space = await db.get(BusinessRecord, data.get('space_id'))
    mapping = (space.data or {}) if space is not None else {}
    if not isinstance(mapping, dict):
        raise HTTPException(409, '个人空间目录映射格式无效')
    folder = str(mapping.get('folder', ''))
    if (space is None or space.module != SPACE_MODULE or space.serial_no != f"PAIS-U{data['owner_user_id']}"
            or space.owner != owner.username
            or mapping.get('owner_user_id') != data.get('owner_user_id')
            or mapping.get('bucket') != bucket or mapping.get('endpoint') != endpoint
            or data.get('endpoint') != endpoint or location is None or location[0] != bucket
            or not location[1].startswith(prefix + '/') or not folder.startswith(prefix + '/personal/')
            or not folder.endswith('--u' + str(data['owner_user_id'])) or '\\' in folder
            or any(p in {'', '.', '..'} for p in folder.split('/'))
            or re.fullmatch(r'[a-f0-9]{64}', str(data.get('sha256', ''))) is None):
        raise HTTPException(409, '个人文件存储与真实账号目录映射不一致')
    identity['_personal_revision_folder'] = folder
    return record, item, identity


async def personal_session_context(file_id, session_id, identity, db, *, terminal=False, lock=False):
    record, item, identity = await personal_attachment_context(file_id, identity, db, lock=lock)
    session = copy.deepcopy((record.data.get('libreoffice_sessions') or {}).get(session_id))
    if (not isinstance(session, dict) or session.get('scope') != 'personal' or session.get('file_id') != file_id
            or session.get('user') != identity['username'] or session.get('attachment_id') != item.id
            or session.get('owner_user_id') != record.data['owner_user_id'] or item.record_id != record.id
            or session.get('revision_folder') != identity['_personal_revision_folder']
            or session.get('endpoint') != record.data['endpoint']):
        raise HTTPException(404, '个人编辑会话不存在或归属已变化')
    context = OfficeContext(record, item, session, identity)
    if not terminal:
        require_lease(context)
    return context


async def create_personal_session(file_id, identity, db):
    config = editor_configuration(personal=True)
    record, item, identity = await personal_attachment_context(file_id, identity, db)
    _ensure_case_word_editor_not_locked(item)
    snapshot = {name: getattr(item, name) for name in ('path', 'stored_name', 'original_name', 'size', 'content_type')}
    expected_hash = record.data['sha256']
    await db.rollback()
    info = await discovery(personal=True)
    content = await read_document(SimpleNamespace(**snapshot))
    version = validate_docx(content)
    if version != expected_hash or len(content) != snapshot['size']:
        raise HTTPException(409, '个人文件实际内容与登记摘要不一致')
    record, item, identity = await personal_attachment_context(file_id, identity, db, lock=True)
    if item.path != snapshot['path'] or record.data['sha256'] != version:
        raise HTTPException(409, '读取期间文件版本已变化，请重新打开')
    _ensure_case_word_editor_not_locked(item)
    if item.record_id != record.id:
        # Keep the original case document and its lease completely untouched.
        item = FileAttachment(record_id=record.id, category='个人AI空间', uploader=record.owner,
                              remark='个人编辑独立附件；原案件附件保留', **snapshot)
        db.add(item)
        await db.flush()
        record.data = {**record.data, 'original_attachment_id': record.data['attachment_id'], 'attachment_id': item.id}
    now = now_utc().replace(microsecond=0)
    session_id, lease_token = uuid4().hex, secrets.token_urlsafe(48)
    expires = now + timedelta(seconds=settings.office_editor_token_seconds)
    result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == item.id, FileAttachment.record_id == record.id, FileAttachment.path == snapshot['path'],
        or_(FileAttachment.word_editor_lock_token == '', FileAttachment.word_editor_lock_expires_at.is_(None),
            FileAttachment.word_editor_lock_expires_at <= now),
    ).values(word_editor_lock_token=lease_token, word_editor_locked_by=identity['username'],
             word_editor_lock_expires_at=min(expires, now + timedelta(seconds=settings.office_editor_lease_seconds)))
        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, '文件已被其他编辑会话占用')
    session = {'id': session_id, 'scope': 'personal', 'file_id': file_id, 'owner_user_id': record.data['owner_user_id'],
               'attachment_id': item.id, 'user': identity['username'], 'token_id': uuid4().hex, 'lease_token': lease_token,
               'expires_at': expires.isoformat(), 'status': 'opening', 'save_status': 'idle',
               'path': item.path, 'version': version, 'size': len(content), 'modified_at': iso_utc(now),
               'wopi_lock': '', 'engine_started': False, 'close_requested': False, 'pending': None, 'error': None,
               'revision_folder': identity['_personal_revision_folder'], 'endpoint': record.data['endpoint']}
    store_session(OfficeContext(record, item, session, identity))
    await db.commit()
    return {'session_id': session_id, 'editor_url': editor_url(info, session_id, personal=True),
            'access_token': session_token(session), 'access_token_ttl': int(expires.timestamp() * 1000),
            'expires_at': expires.isoformat(), 'filename': record.data['name'],
            'editor_origin': origin(config['browser']),
            'postmessage_origin': config['frontend']}


async def personal_capability(file_id, identity, db):
    try:
        _, item, _ = await personal_attachment_context(file_id, identity, db)
        _ensure_case_word_editor_not_locked(item)
        return {'editable': True, 'edit_unavailable_reason': ''}
    except HTTPException as exc:
        return {'editable': False, 'edit_unavailable_reason': str(exc.detail)}


async def get_personal_session(file_id, session_id, identity, db):
    return status_payload(await personal_session_context(file_id, session_id, identity, db, terminal=True))


async def close_personal_session(file_id, session_id, identity, db):
    context = await personal_session_context(file_id, session_id, identity, db, terminal=True, lock=True)
    status = status_payload(context)
    if status['status'] in {'closed', 'expired'}:
        return status
    if context.session['save_status'] == 'error':
        raise HTTPException(409, {'message': '保存失败，必须保留编辑器并重试保存', **status})
    context.session['close_requested'] = True
    cancel = not context.session['wopi_lock'] and not context.session['pending']
    context.session['status'] = 'closed' if cancel else 'closing'
    await persist_context(context, db, release=cancel)
    await db.refresh(context.item)
    return status_payload(context)
