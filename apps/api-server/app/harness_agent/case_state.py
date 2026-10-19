"""OA 案件会话和确认状态存储；沿用历史检查点格式，不创建或执行图引擎。"""
from contextlib import asynccontextmanager
from copy import deepcopy


class CaseStateStore:
    def __init__(self, url: str):
        self.url = url
        self.backend = "postgresql" if url.startswith(("postgresql://", "postgres://")) else "memory"
        self._context = None
        self._saver = None
        self._memory = {}
        self._locks = {}

    async def start(self):
        if self.backend == "postgresql":
            # 仅使用既有存储协议保留历史消息和确认记录，不导入 langgraph.graph。
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            self._context = AsyncPostgresSaver.from_conn_string(self.url)
            try:
                self._saver = await self._context.__aenter__()
                await self._saver.setup()
            except Exception:
                await self.close()
                raise

    async def close(self):
        if self._context:
            await self._context.__aexit__(None, None, None)
        self._context = self._saver = None

    @asynccontextmanager
    async def operation(self, thread_id):
        import asyncio
        from app.core.process_coordination import session_advisory_lock
        from app.database import engine

        lock = self._locks.setdefault(thread_id, asyncio.Lock())
        async with lock:
            async with session_advisory_lock(engine, "oa-case-state:" + thread_id):
                yield

    async def read(self, thread_id):
        if self.backend == "memory":
            return deepcopy(self._memory.get(thread_id, {}))
        saved = await self._saver.aget_tuple({"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}})
        if saved is None:
            return {}
        return deepcopy({name: value for name, value in saved.checkpoint["channel_values"].items()
                         if not name.startswith(("__", "branch:"))})

    async def write(self, thread_id, state):
        if self.backend == "memory":
            self._memory[thread_id] = deepcopy(state)
            return
        from langgraph.checkpoint.base import empty_checkpoint

        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        previous = await self._saver.aget_tuple(config)
        checkpoint = empty_checkpoint()
        versions = previous.checkpoint["channel_versions"] if previous else {}
        new_versions = {name: self._saver.get_next_version(versions.get(name), None) for name in state}
        checkpoint.update(channel_values=deepcopy(state), channel_versions=new_versions,
                          updated_channels=list(state))
        metadata = {"source": "update", "step": int(previous.metadata.get("step", -1)) + 1 if previous else 0,
                    "parents": {}, "runtime": "deepseek-harness"}
        await self._saver.aput(previous.config if previous else config, checkpoint, metadata, new_versions)
