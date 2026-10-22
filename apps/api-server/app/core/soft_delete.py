"""逻辑删除：业务数据不做物理删除，只标记删除时间和删除人，查询自动过滤已删除的行。

统一在数据库访问层拦截，不逐处改业务代码：
- 业务表追加 deleted_at / deleted_by 两列（install）；技术/派生/历史导入表不参与（EXCLUDED_TABLES 和 legacy 前缀）。
- 所有 ORM 查询自动附加 deleted_at IS NULL（do_orm_execute + with_loader_criteria）；需要看已删除数据时用 include_deleted=True。
- session.delete(obj) 和 delete(...) 语句改写成“标记已删除”；原数据库层的 ON DELETE CASCADE 由本模块同步标记子记录，RESTRICT 仍然阻止删除。
- 唯一约束改成“只对未删除的行生效”的部分唯一索引，删除后原编号/账号/名称可以重新使用。
- 系统维护确需物理清理时显式使用 hard_delete 逃生口（session.info["hard_delete"] = True 或语句选项 hard_delete=True）。
"""

from contextvars import ContextVar
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint, event, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy.orm.attributes import set_committed_value

# 不做逻辑删除的表：技术数据、派生/重建数据、访问令牌、通知投递等；它们仍可物理清理。
EXCLUDED_TABLES = frozenset({
    "mcp_access_tokens", "mcp_call_logs", "notification_deliveries", "notification_sync_schedules", "notifications",
    "security_policies", "system_configs", "role_permissions", "party_library",
})
_PARTIAL_WHERE = {"postgresql_where": text("deleted_at IS NULL"), "sqlite_where": text("deleted_at IS NULL")}

actor_var: ContextVar[str] = ContextVar("soft_delete_actor", default="system")
_soft_tables: dict[str, type] = {}  # 表名 -> 映射类
_edges_by_parent: dict[str, list] = {}


class SoftDeleteMixin:
    """让 with_loader_criteria 一次匹配所有参与逻辑删除的类。"""

    # 占位：with_loader_criteria 会先用混入类本身分析条件表达式；各映射类自己的列在 install 里单独添加。
    deleted_at = Column("deleted_at", DateTime(timezone=True), nullable=True)


def is_soft_table_name(name: str) -> bool:
    # legacy_* 与大写前缀（AWS_/CRM_/FCM_/Legal_）是旧系统导入的只读历史数据，不参与。
    return name not in EXCLUDED_TABLES and not name.startswith("legacy_") and name == name.lower()


def soft_tables() -> dict[str, type]:
    return _soft_tables


def keep_deleted_file(path) -> None:
    """删除业务记录后，附件文件本体保留在存储里不物理删除（回收站恢复时文件还在）。"""
    return None


def set_actor(username: str | None) -> None:
    actor_var.set((username or "system")[:64])


def install(base) -> None:
    """模型全部加载后调用一次：加列、改部分唯一索引、登记外键级联关系。"""
    for mapper in list(base.registry.mappers):
        cls, table = mapper.class_, mapper.local_table
        if not is_soft_table_name(table.name) or table.name in _soft_tables:
            continue  # 可重复调用：只处理还没处理过的类
        setattr(cls, "deleted_at", Column("deleted_at", DateTime(timezone=True), nullable=True))
        setattr(cls, "deleted_by", Column("deleted_by", String(64), nullable=True))
        cls.__bases__ = (*cls.__bases__, SoftDeleteMixin)
        _soft_tables[table.name] = cls
        _make_unique_partial(table)
        # 回收站按“已删除”筛选：只给已删除的行建索引，体积很小。
        Index(f"ix_{table.name}_deleted_at", table.c.deleted_at, postgresql_where=text("deleted_at IS NOT NULL"), sqlite_where=text("deleted_at IS NOT NULL"))
    _edges_by_parent.clear()
    for table in base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            if fk.ondelete in {"CASCADE", "RESTRICT"}:
                _edges_by_parent.setdefault(fk.column.table.name, []).append((table, fk.parent, fk.ondelete))


def _make_unique_partial(table) -> None:
    """唯一约束只对未删除的行生效；同一组列的重复声明（约束 + 唯一索引）合并成一个部分唯一索引。"""
    groups: dict[tuple, str] = {}
    for index in [i for i in table.indexes if i.unique]:
        table.indexes.discard(index)
        groups.setdefault(tuple(c.name for c in index.columns), index.name)
    for constraint in [c for c in table.constraints if isinstance(c, UniqueConstraint)]:
        table.constraints.discard(constraint)
        names = tuple(c.name for c in constraint.columns)
        groups.setdefault(names, constraint.name or f"uq_{table.name}_" + "_".join(names))
    for column in table.columns:
        if column.unique:
            column.unique = False
            groups.setdefault((column.name,), f"uq_{table.name}_{column.name}")
    taken = {i.name for i in table.indexes}
    for names, name in groups.items():
        if name in taken:
            name += "_live"
        Index(name, *[table.c[n] for n in names], unique=True, **_PARTIAL_WHERE)
        taken.add(name)


def partial_unique_index_specs() -> list[tuple[str, str, list[str]]]:
    """迁移用：（表名, 索引名, 列名）清单，生产库据此把原唯一约束/唯一索引换成部分唯一索引。"""
    return [(name, index.name, [c.name for c in index.columns])
            for name, cls in _soft_tables.items() for index in cls.__table__.indexes if index.unique]


# ---------- 级联同步 ----------

def _pk(table):
    return list(table.primary_key.columns)[0]


def _mark_children(connection, table, ids, now, actor, seen, exempt) -> None:
    """按 ON DELETE CASCADE 递归标记子记录；仍有未删除的 RESTRICT 子记录时拒绝（与同批一起删除的除外）。"""
    for child, column, action in _edges_by_parent.get(table.name, []):
        if action == "CASCADE" and child.name not in _soft_tables:
            continue  # 技术表里的级联子记录保持原样，不物理删除
        live = [child.c.deleted_at.is_(None)] if "deleted_at" in child.c else []
        child_pk = _pk(child)
        rows = [r[0] for r in connection.execute(select(child_pk).where(column.in_(ids), *live))]
        if action == "RESTRICT":
            blockers = [r for r in rows if (child.name, r) not in exempt]
            if blockers:
                raise IntegrityError("DELETE", {}, Exception(f"{child.name}.{column.name} 仍引用 {table.name}，存在关联数据，不能删除"))
            continue
        rows = [r for r in rows if (child.name, r) not in seen]
        if rows:
            seen.update((child.name, r) for r in rows)
            _mark_children(connection, child, rows, now, actor, seen, exempt)
            connection.execute(update(child).where(child_pk.in_(rows)).values(deleted_at=now, deleted_by=actor))


def _now():
    return datetime.now(timezone.utc)


# ---------- 事件 ----------

def _hard_delete_requested(session) -> bool:
    return bool(session.info.get("hard_delete"))


@event.listens_for(Session, "before_flush")
def _soft_delete_flush(session, flush_context, instances):
    """session.delete(obj) → 标记已删除。取消对应的 DELETE，对象自身的删除标记随会话外的 UPDATE 落库。"""
    if _hard_delete_requested(session):
        return
    targets = [obj for obj in list(session.deleted) if isinstance(obj, SoftDeleteMixin)]
    if not targets:
        return
    now, actor = _now(), actor_var.get()
    connection = session.connection()
    exempt = {(o.__table__.name, getattr(o, _pk(o.__table__).name)) for o in targets}
    seen = set(exempt)
    for obj in targets:
        table = obj.__table__
        row_id = getattr(obj, _pk(table).name)
        _mark_children(connection, table, [row_id], now, actor, seen, exempt)
        connection.execute(update(table).where(_pk(table) == row_id, table.c.deleted_at.is_(None)).values(deleted_at=now, deleted_by=actor))
        set_committed_value(obj, "deleted_at", now)
        set_committed_value(obj, "deleted_by", actor)
        session.expunge(obj)  # 取消这条 DELETE；行已被上面标记


@event.listens_for(Session, "do_orm_execute")
def _soft_delete_execute(state):
    if state.execution_options.get("include_deleted") or state.execution_options.get("hard_delete") or _hard_delete_requested(state.session):
        return None
    statement = state.statement
    if state.is_delete:
        table = getattr(statement, "table", None)
        if getattr(table, "name", None) in _soft_tables:
            return _soft_delete_statement(state, statement, table)
    if (state.is_select and not state.is_column_load and not state.is_relationship_load) or state.is_update or state.is_delete:
        state.statement = statement.options(with_loader_criteria(
            SoftDeleteMixin, lambda cls: cls.deleted_at.is_(None), include_aliases=True))
    return None


def _soft_delete_statement(state, statement, table):
    """delete(Model).where(...) 改写成逻辑删除：先取出命中的主键，同步标记级联子记录，再标记本表。"""
    connection = state.session.connection()
    pk = _pk(table)
    ids = [row[0] for row in connection.execute(select(pk).where(table.c.deleted_at.is_(None), *getattr(statement, "_where_criteria", ())))]
    now, actor = _now(), actor_var.get()
    if ids:
        seen = {(table.name, i) for i in ids}
        _mark_children(connection, table, ids, now, actor, seen, set(seen))
    result = state.invoke_statement(
        statement=update(table).where(pk.in_(ids), table.c.deleted_at.is_(None)).values(deleted_at=now, deleted_by=actor),
        execution_options={"synchronize_session": False})
    # 原语句是 DELETE：命中的对象要从会话里移走，之后 session.get() 不能再返回它们。
    id_set = set(ids)
    for obj in list(state.session.identity_map.values()):
        if getattr(getattr(obj, "__table__", None), "name", None) == table.name and getattr(obj, pk.name, None) in id_set:
            set_committed_value(obj, "deleted_at", now)
            set_committed_value(obj, "deleted_by", actor)
            state.session.expunge(obj)
    return result


# ---------- 恢复 ----------

def restore_rows(session_sync, table_name: str, ids: list) -> int:
    """恢复已删除的行，连同同一次删除级联标记的子记录。与现有未删除数据冲突时抛 IntegrityError。"""
    table = _soft_tables[table_name].__table__
    connection = session_sync.connection()
    pk = _pk(table)
    count = 0
    for row_id, stamp in connection.execute(select(pk, table.c.deleted_at).where(pk.in_(ids), table.c.deleted_at.is_not(None))).all():
        _restore(connection, table, [row_id], stamp)
        count += 1
    return count


def _restore(connection, table, ids, stamp) -> None:
    pk = _pk(table)
    connection.execute(update(table).where(pk.in_(ids), table.c.deleted_at == stamp).values(deleted_at=None, deleted_by=None))
    for child, column, action in _edges_by_parent.get(table.name, []):
        if action != "CASCADE" or child.name not in _soft_tables:
            continue
        child_pk = _pk(child)
        rows = [r[0] for r in connection.execute(select(child_pk).where(column.in_(ids), child.c.deleted_at == stamp))]
        if rows:
            _restore(connection, child, rows, stamp)
