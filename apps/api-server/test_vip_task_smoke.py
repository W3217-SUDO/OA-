"""Isolated persistence smoke test for the VIP task API commands."""
import asyncio
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.main import (
    VipTaskInput, VipTaskMessageInput, VipTaskMessageReadInput, VipTaskNodeInput,
    VipTaskNodeUpdateInput, VipTaskUpdateInput, create_vip_task, create_vip_task_message,
    create_vip_task_node, delete_vip_task, delete_vip_task_node, list_vip_tasks, read_vip_task_messages,
    update_vip_task, update_vip_task_node,
)
from app.models import User, VipTask, VipTaskMessage, VipTaskNode


async def run() -> None:
    path = Path(__file__).with_name("vip-task-smoke.db")
    journal = Path(f"{path}-journal")
    for candidate in (path, journal):
        if candidate.exists():
            candidate.unlink()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    admin = {"username": "admin", "role": "admin"}
    owner = {"username": "owner", "role": "user"}
    outsider = {"username": "outsider", "role": "user"}
    async with session_factory() as db:
        db.add_all([
            User(username="admin", password_hash="x", role="admin"),
            User(username="owner", password_hash="x", role="user"),
            User(username="outsider", password_hash="x", role="user"),
        ])
        await db.commit()
        task = await create_vip_task(VipTaskInput(title="CODEX-VIP", customer="客户甲", owner="owner", collaborators=[]), admin, db)
        assert (await list_vip_tasks(customer="客户甲", page=1, page_size=15, identity=admin, db=db))["total"] == 1
        assert (await list_vip_tasks(page=1, page_size=15, identity=outsider, db=db))["total"] == 0
        node = await create_vip_task_node(task["id"], VipTaskNodeInput(title="节点", owner="owner"), admin, db)
        try:
            await update_vip_task(task["id"], VipTaskUpdateInput(status="处理中"), outsider, db)
            raise AssertionError("non-member status update was accepted")
        except HTTPException as error:
            assert error.status_code == 403
        await update_vip_task(task["id"], VipTaskUpdateInput(status="处理中"), owner, db)
        try:
            await update_vip_task(task["id"], VipTaskUpdateInput(status="已完成"), owner, db)
            raise AssertionError("unfinished node did not block task completion")
        except HTTPException as error:
            assert error.status_code == 409
        await update_vip_task_node(task["id"], node["id"], VipTaskNodeUpdateInput(status="处理中"), owner, db)
        await update_vip_task_node(task["id"], node["id"], VipTaskNodeUpdateInput(status="已完成"), owner, db)
        await update_vip_task(task["id"], VipTaskUpdateInput(status="已完成"), owner, db)
        try:
            await update_vip_task(task["id"], VipTaskUpdateInput(status="已验收"), owner, db)
            raise AssertionError("owner accepted a task created by another user")
        except HTTPException as error:
            assert error.status_code == 403
        assert (await read_vip_task_messages(task["id"], VipTaskMessageReadInput(), owner, db))["updated"] == 1
        await update_vip_task(task["id"], VipTaskUpdateInput(status="待处理"), admin, db)
        await update_vip_task(task["id"], VipTaskUpdateInput(status="处理中"), owner, db)
        await update_vip_task(task["id"], VipTaskUpdateInput(status="已完成"), owner, db)
        await update_vip_task(task["id"], VipTaskUpdateInput(status="已验收"), admin, db)
        try:
            await create_vip_task_message(task["id"], VipTaskMessageInput(content="越权", recipients=["outsider"]), owner, db)
            raise AssertionError("non-member recipient was accepted")
        except HTTPException as error:
            assert error.status_code == 403
        assert (await read_vip_task_messages(task["id"], VipTaskMessageReadInput(), admin, db))["updated"] == 0
        await create_vip_task_message(task["id"], VipTaskMessageInput(content="节点消息", recipients=["admin"], node_id=node["id"]), owner, db)
        await delete_vip_task_node(task["id"], node["id"], admin, db)
        assert not await db.scalar(select(func.count()).select_from(VipTaskMessage).where(VipTaskMessage.vip_task_node_id == node["id"]))
        await delete_vip_task(task["id"], admin, db)
        assert not await db.scalar(select(func.count()).select_from(VipTask))
        assert not await db.scalar(select(func.count()).select_from(VipTaskNode))
        assert not await db.scalar(select(func.count()).select_from(VipTaskMessage))
    await engine.dispose()
    for candidate in (path, journal):
        if candidate.exists():
            candidate.unlink()


if __name__ == "__main__":
    asyncio.run(run())
