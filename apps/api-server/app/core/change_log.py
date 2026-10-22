"""数据变更留痕：业务表的每次新增、修改、删除、恢复都记下变更前后的值、操作人和来源（网页/MCP/智能体/系统），可一键还原。

和逻辑删除一样在数据库访问层统一拦截，不逐个接口改：
- ORM 工作单元（session.add / 改属性 / session.delete）：after_flush 时按属性历史记录；
- update(Model) 语句：执行前后各读一次受影响行，记录前后值；
- 逻辑删除与恢复：由 soft_delete 在标记时调用 record_rows()。
只记业务表（逻辑删除覆盖的表），追加型日志表和时间戳列不记；JSON 列只记变动的键。
"""

from contextvars import ContextVar
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import Date, DateTime, Integer, Numeric, event, insert, select, update
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core import soft_delete

source_var: ContextVar[str] = ContextVar("change_source", default="system")
_revert_of: ContextVar[int | None] = ContextVar("change_revert_of", default=None)

# 只要动了数据库就留记录；只有这几类不记：日志表本身（本来就是痕迹）、发送队列、系统自动重建的派生数据。
SKIP_TABLES = frozenset({
    "data_change_logs", "mcp_call_logs",
    "workflow_events", "contract_events", "contract_object_logs", "jar_fee_audit_logs", "ipr_fee_audit_logs",
    "law_firm_audits", "seal_asset_audits", "ipr_case_logs",
    "notification_deliveries", "notification_sync_schedules", "party_library",
})
MAX_FLUSH_INSERTS = 2000  # 一次导入超过这个数量时，按表只记一条摘要
# business_records 里本身就是痕迹的模块（组织审计记录、智能体待确认请求），不再重复留痕。
SKIP_RECORD_MODULES = frozenset({"organization_audit", "agent_mcp_action"})
SKIP_COLUMNS = frozenset({"updated_at", "updated_by", "created_at", "deleted_at", "deleted_by"})
SUMMARY_COLUMNS = ("serial_no", "title", "name", "original_name", "code", "username")
MAX_STATEMENT_ROWS = 2000
ABSENT = "__absent__"  # JSON 键原来不存在
UNKNOWN = "__unknown__"  # 修改前的值未加载，无法确定


def set_source(value: str):
    return source_var.set(value)


_mapped: dict[str, type] = {}


def mapped_classes() -> dict[str, type]:
    if not _mapped:
        from app.database import Base
        _mapped.update({mapper.local_table.name: mapper.class_ for mapper in Base.registry.mappers})
    return _mapped


def loggable(table_name: str) -> bool:
    return table_name in mapped_classes() and table_name not in SKIP_TABLES


def _row_snapshot(obj_or_row, table) -> dict:
    """真删除前的整行内容（用于追溯和按原样插回）。"""
    if hasattr(obj_or_row, "__table__"):
        state = sa_inspect(obj_or_row)  # 只读已加载的值，不触发懒加载（行可能已删除）
        return {attr.columns[0].name: _plain(state.dict.get(attr.key)) for attr in state.mapper.column_attrs}
    return {column.name: _plain(obj_or_row.get(column.name)) for column in table.columns}


def _plain(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(value)} 字节>"
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _diff(before, after):
    """返回可存的差异；没有变化返回 None。dict 列只记变动的键。"""
    if isinstance(before, dict) and isinstance(after, dict):
        keys = {k for k in set(before) | set(after) if before.get(k, ABSENT) != after.get(k, ABSENT)}
        if not keys:
            return None
        return {"__json__": {k: [_plain(before.get(k, ABSENT)), _plain(after.get(k, ABSENT))] for k in sorted(keys, key=str)}}
    if before == after:
        return None
    return [_plain(before), _plain(after)]


def _summary_from(getter) -> str:
    for name in SUMMARY_COLUMNS:
        value = getter(name)
        if value not in (None, ""):
            return str(value)[:255]
    return ""


def _entry(table_name, row_id, action, changes, summary):
    return {"table_name": table_name, "row_id": str(row_id), "action": action, "changes": changes or {}, "summary": summary or "",
            "actor": soft_delete.actor_var.get(), "source": source_var.get(), "created_at": datetime.now(timezone.utc),
            "revert_of": _revert_of.get()}


_table_ready: dict[int, bool] = {}


def _write(connection, entries) -> None:
    if not entries:
        return
    from app.data_models.change_logs import DataChangeLog
    key = id(connection.engine)
    if key not in _table_ready:  # 每个数据库只查一次留痕表在不在（只建了部分表的测试库没有这张表）
        _table_ready[key] = sa_inspect(connection).has_table(DataChangeLog.__tablename__)
    if _table_ready[key]:
        connection.execute(insert(DataChangeLog.__table__), entries)


def record_rows(connection, table, ids, action) -> None:
    """逻辑删除 / 恢复时由 soft_delete 调用：按行记一条 delete / restore。"""
    if not ids or not loggable(table.name):
        return
    pk = list(table.primary_key.columns)[0]
    columns = [table.c[name] for name in SUMMARY_COLUMNS if name in table.c]
    summaries = {}
    if columns:
        for row in connection.execute(select(pk, *columns).where(pk.in_(list(ids)))).mappings():
            summaries[row[pk.name]] = _summary_from(lambda name, row=row: row.get(name))
    _write(connection, [_entry(table.name, row_id, action, {}, summaries.get(row_id, "")) for row_id in ids])


@event.listens_for(Session, "before_flush")
def _snapshot_hard_deletes(session, flush_context, instances):
    """真删除的对象在 DELETE 执行前读全整行（此时还能加载未取的列），供 after_flush 存档。"""
    if session.info.get("skip_change_log"):
        return
    snapshots = session.info.setdefault("_change_log_snapshots", {})
    for obj in list(session.deleted):
        table = getattr(obj, "__table__", None)
        if table is None or not loggable(table.name) or table.name in soft_delete.soft_tables():
            continue
        state = sa_inspect(obj)
        snapshots[id(obj)] = {attr.columns[0].name: _plain(getattr(obj, attr.key)) for attr in state.mapper.column_attrs}


@event.listens_for(Session, "after_flush")
def _after_flush(session, flush_context):
    if session.info.get("skip_change_log"):
        return
    entries = []
    inserts: dict[str, list] = {}
    for obj in list(session.new):
        table = getattr(obj, "__table__", None)
        if table is None or not loggable(table.name) or getattr(obj, "module", None) in SKIP_RECORD_MODULES:
            continue
        inserts.setdefault(table.name, []).append(obj)
    for name, objects in inserts.items():
        if len(objects) > MAX_FLUSH_INSERTS:
            entries.append(_entry(name, 0, "insert", {"__bulk__": f"一次新增 {len(objects)} 行，仅记录摘要"}, ""))
            continue
        for obj in objects:
            pk = list(obj.__table__.primary_key.columns)[0].name
            entries.append(_entry(name, getattr(obj, pk), "insert", {}, _summary_from(lambda column, obj=obj: getattr(obj, column, None))))
    for obj in list(session.deleted):  # 不参与逻辑删除的表是真删除：删前整行存档
        table = getattr(obj, "__table__", None)
        if table is None or not loggable(table.name) or table.name in soft_delete.soft_tables():
            continue
        snapshot = session.info.get("_change_log_snapshots", {}).pop(id(obj), None) or _row_snapshot(obj, table)
        pk = list(table.primary_key.columns)[0].name
        entries.append(_entry(table.name, snapshot.get(pk), "delete", {"__row__": snapshot},
                              _summary_from(lambda column: snapshot.get(column))))
    for obj in list(session.dirty):
        table = getattr(obj, "__table__", None)
        if table is None or not loggable(table.name) or getattr(obj, "module", None) in SKIP_RECORD_MODULES:
            continue
        state = sa_inspect(obj)
        if state.deleted or state.detached:
            continue
        changes = {}
        for attr in state.mapper.column_attrs:
            column = attr.columns[0]
            if column.name in SKIP_COLUMNS or column.name not in table.c:
                continue
            history = state.attrs[attr.key].history
            if not history.has_changes():
                continue
            before = history.deleted[0] if history.deleted else UNKNOWN
            after = history.added[0] if history.added else None
            change = _diff(before, after)
            if change is not None:
                changes[column.name] = change
        if changes:
            pk = list(table.primary_key.columns)[0].name
            entries.append(_entry(table.name, getattr(obj, pk), "update", changes, _summary_from(lambda name: getattr(obj, name, None))))
    _write(session.connection(), entries)


def _column_names(statement, table):
    values = getattr(statement, "_values", None) or {}
    names = []
    for key in values:
        name = getattr(key, "key", None) or getattr(key, "name", None) or str(key)
        if name in table.c and name not in SKIP_COLUMNS:
            names.append(name)
    return names


@event.listens_for(Session, "do_orm_execute")
def _log_update_statement(state):
    """update(Model).where(...).values(...)：执行前后各读一次受影响行，按行记录变更前后值。"""
    if state.session.info.get("skip_change_log") or state.execution_options.get("skip_change_log"):
        return None
    if state.is_delete:
        return _log_delete_statement(state)
    if state.is_insert:
        return _log_insert_statement(state)
    if not state.is_update:
        return None
    statement = state.statement
    table = getattr(statement, "table", None)
    if table is None or not loggable(getattr(table, "name", "")):
        return None
    names = _column_names(statement, table)
    if not names:
        return None
    connection = state.session.connection()
    pk = list(table.primary_key.columns)[0]
    criteria = list(getattr(statement, "_where_criteria", ()))
    live = [] if state.execution_options.get("include_deleted") or "deleted_at" not in table.c else [table.c.deleted_at.is_(None)]
    columns = [table.c[name] for name in names]
    summary_columns = [table.c[name] for name in SUMMARY_COLUMNS if name in table.c and name not in names]
    before = {row[pk.name]: row for row in connection.execute(
        select(pk, *columns, *summary_columns).where(*criteria, *live).limit(MAX_STATEMENT_ROWS + 1)).mappings()}
    result = state.invoke_statement()
    if not before:
        return result
    if len(before) > MAX_STATEMENT_ROWS:
        _write(connection, [_entry(table.name, 0, "update", {"__bulk__": f"批量修改超过 {MAX_STATEMENT_ROWS} 行，仅记录摘要", "columns": names}, "")])
        return result
    after = {row[pk.name]: row for row in connection.execute(select(pk, *columns).where(pk.in_(list(before)))).mappings()}
    entries = []
    for row_id, old in before.items():
        new = after.get(row_id)
        if new is None:
            continue
        changes = {}
        for name in names:
            change = _diff(old[name], new[name])
            if change is not None:
                changes[name] = change
        if changes:
            entries.append(_entry(table.name, row_id, "update", changes, _summary_from(lambda name, old=old: old.get(name))))
    _write(connection, entries)
    return result


def _log_insert_statement(state):
    """insert(...) 语句（批量导入等）：拿不到逐行编号，按表记一条摘要（插入行数）。"""
    table = getattr(state.statement, "table", None)
    if table is None or not loggable(getattr(table, "name", "")):
        return None
    result = state.invoke_statement()
    count = getattr(result, "rowcount", -1)
    _write(state.session.connection(), [_entry(table.name, 0, "insert", {"__bulk__": f"批量新增 {count if count >= 0 else '若干'} 行"}, "")])
    return result


def _log_delete_statement(state):
    """delete(...) 语句落在不参与逻辑删除的表上（真删除）：删前把每一行整行存档。逻辑删除表由 soft_delete 处理。"""
    statement = state.statement
    table = getattr(statement, "table", None)
    if table is None or not loggable(getattr(table, "name", "")) or table.name in soft_delete.soft_tables():
        return None
    connection = state.session.connection()
    pk = list(table.primary_key.columns)[0]
    rows = connection.execute(select(table).where(*getattr(statement, "_where_criteria", ())).limit(MAX_STATEMENT_ROWS + 1)).mappings().all()
    if len(rows) > MAX_STATEMENT_ROWS:
        entries = [_entry(table.name, 0, "delete", {"__bulk__": f"批量删除超过 {MAX_STATEMENT_ROWS} 行，仅记录摘要"}, "")]
    else:
        entries = [_entry(table.name, row[pk.name], "delete", {"__row__": _row_snapshot(row, table)}, _summary_from(lambda name, row=row: row.get(name)))
                   for row in rows]
    result = state.invoke_statement()
    _write(connection, entries)
    return result


# ---------- 查询与还原 ----------

def _coerce(column, value):
    if value is None:
        return None
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date) and isinstance(value, str):
        return date.fromisoformat(value)
    if isinstance(column.type, Numeric) and isinstance(value, str):
        return Decimal(value)
    return value


async def revert(db, log_id: int, operator: str, *, force: bool = False) -> dict:
    """把一条变更还原：修改→改回原值；新增→逻辑删除；删除→恢复；恢复→再删除。还原本身也会留痕。"""
    from app.data_models.change_logs import DataChangeLog
    log = await db.scalar(select(DataChangeLog).where(DataChangeLog.id == log_id))
    if log is None:
        raise HTTPException(404, "变更记录不存在")
    if log.reverted_at is not None:
        raise HTTPException(409, "这条变更已经还原过")
    cls = mapped_classes().get(log.table_name)
    if cls is None or log.row_id in ("", "0"):
        raise HTTPException(409, "这条变更不支持还原")
    soft = log.table_name in soft_delete.soft_tables()
    table = cls.__table__
    pk = list(table.primary_key.columns)[0]
    try:
        row_id = int(log.row_id) if isinstance(pk.type, Integer) else log.row_id
    except ValueError:
        raise HTTPException(409, "这条变更的行号无效，不能还原") from None
    source_token, revert_token = source_var.set("web"), _revert_of.set(log.id)
    soft_delete.set_actor(operator)
    try:
        if log.action in {"insert", "restore"}:
            obj = await db.get(cls, row_id)
            if obj is None:
                raise HTTPException(409, "这条数据已经不存在或已被删除")
            await db.delete(obj)
        elif log.action == "delete" and soft:
            restored = await db.run_sync(lambda session: soft_delete.restore_rows(session, log.table_name, [row_id]))
            if not restored:
                raise HTTPException(409, "这条数据当前不是已删除状态，无需恢复")
        elif log.action == "delete":  # 真删除的表：按删前整行存档插回
            snapshot = (log.changes or {}).get("__row__")
            if not snapshot:
                raise HTTPException(409, "这条删除没有整行存档，不能还原")
            if await db.get(cls, row_id) is not None:
                raise HTTPException(409, "同一编号的数据已经存在，不能重复插回")
            values = {name: _coerce(table.c[name], value) for name, value in snapshot.items()
                      if name in table.c and not (value is None and (table.c[name].default is not None or table.c[name].server_default is not None))}
            await db.execute(insert(table).values(values).execution_options(skip_change_log=True))
            await db.run_sync(lambda session: record_rows(session.connection(), table, [row_id], "restore"))
        elif log.action == "update":
            names = [name for name in log.changes if name in table.c]
            current = (await db.execute(select(*[table.c[n] for n in names]).where(pk == row_id)
                                        .execution_options(include_deleted=True))).mappings().first() if names else None
            if current is None:
                raise HTTPException(409, "这条数据已经不存在")
            values, conflicts, skipped = {}, [], []
            for name in names:
                change = log.changes[name]
                if isinstance(change, dict) and "__json__" in change:
                    now = dict(current[name] or {})
                    for key, (old, new) in change["__json__"].items():
                        if _plain(now.get(key, ABSENT)) != new:
                            conflicts.append(f"{name}.{key}")
                        if old == ABSENT:
                            now.pop(key, None)
                        else:
                            now[key] = old
                    values[name] = now
                    continue
                old, new = change
                if old == UNKNOWN:
                    skipped.append(name)
                    continue
                if _plain(current[name]) != new:
                    conflicts.append(name)
                values[name] = _coerce(table.c[name], old)
            if conflicts and not force:
                raise HTTPException(409, {"detail": "这条数据在这次变更之后又被修改过，直接还原会覆盖后来的修改", "conflicts": conflicts})
            if not values:
                raise HTTPException(409, "没有可还原的字段（修改前的值未记录）")
            await db.execute(update(cls).where(pk == row_id).values(**values).execution_options(include_deleted=True))
        else:
            raise HTTPException(409, "这条变更不支持还原")
        await db.execute(update(DataChangeLog).where(DataChangeLog.id == log.id)
                         .values(reverted_at=datetime.now(timezone.utc), reverted_by=operator))
        await db.commit()
    finally:
        source_var.reset(source_token)
        _revert_of.reset(revert_token)
    return {"reverted": log.id, "table": log.table_name, "row_id": row_id, "action": log.action}
