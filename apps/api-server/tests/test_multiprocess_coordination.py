"""多工作进程运行时的跨进程协调：文件锁、个人智能体对话占用与停止、记忆文件、后台选主。"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from fastapi import HTTPException

from app.areas.personal_agent import conversations, memory_graph
from app.core import process_coordination


def _spawn_sleeper() -> subprocess.Popen:
    """一个真实存活的其他进程，代表另一个 API 工作进程。"""
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])


class FileLockTest(IsolatedAsyncioTestCase):
    async def test_file_lock_excludes_another_process(self):
        path = process_coordination.coordination_path(f"test-lock-{uuid4().hex}")
        path.parent.mkdir(parents=True, exist_ok=True)
        holder = subprocess.Popen([
            sys.executable, "-c",
            "import time\nfrom pathlib import Path\nfrom app.core.process_coordination import file_lock_sync\n"
            f"with file_lock_sync(Path({str(path)!r})):\n"
            "    print('locked', flush=True)\n"
            "    time.sleep(0.6)\n",
        ], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "locked")
            started = time.monotonic()
            async with process_coordination.file_lock(path):
                waited = time.monotonic() - started
            self.assertGreaterEqual(waited, 0.3, "其他进程持锁期间不得进入")
        finally:
            holder.wait(timeout=10)
            holder.stdout.close()
            path.unlink(missing_ok=True)

    async def test_waiting_for_file_lock_does_not_block_event_loop(self):
        path = process_coordination.coordination_path(f"test-loop-{uuid4().hex}")
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        path.parent.mkdir(parents=True, exist_ok=True)
        holder = subprocess.Popen([
            sys.executable, "-c",
            "import time\nfrom pathlib import Path\nfrom app.core.process_coordination import file_lock_sync\n"
            f"with file_lock_sync(Path({str(path)!r})):\n"
            "    print('locked', flush=True)\n"
            "    time.sleep(0.4)\n",
        ], stdout=subprocess.PIPE, text=True)
        task = asyncio.create_task(ticker())
        try:
            self.assertEqual(holder.stdout.readline().strip(), "locked")
            async with process_coordination.file_lock(path):
                pass
            self.assertGreater(ticks, 5, "等待文件锁时本进程其他协程应继续运行")
        finally:
            task.cancel()
            holder.wait(timeout=10)
            holder.stdout.close()
            path.unlink(missing_ok=True)


class PersonalAgentCrossProcessTest(IsolatedAsyncioTestCase):
    def foreign_entry(self, directory: Path, conversation_id: str, pid: int, *, cancellable: bool) -> None:
        registry = conversations._registry_read()
        registry[conversations._operation_key(directory, conversation_id)] = {
            "pid": pid, "cancellable": cancellable, "cancel_requested": False,
        }
        conversations._registry_write(registry)

    async def test_operation_in_another_process_blocks_new_operation_and_delete(self):
        sleeper = _spawn_sleeper()
        try:
            with TemporaryDirectory(prefix="oa-test-mp-busy-") as temporary:
                directory = Path(temporary)
                snapshot = await conversations.create_conversation(directory)
                conversation_id = snapshot["state"]["conversation_id"]
                await conversations.create_conversation(directory)
                self.foreign_entry(directory, conversation_id, sleeper.pid, cancellable=True)
                with self.assertRaises(HTTPException) as raised:
                    async with conversations.conversation_operation(directory, conversation_id):
                        pass
                self.assertEqual(raised.exception.status_code, 409)
                with self.assertRaises(HTTPException) as raised:
                    await conversations.delete_conversation(directory, conversation_id)
                self.assertEqual(raised.exception.status_code, 409)
        finally:
            sleeper.kill()
            sleeper.wait()

    async def test_entry_of_exited_process_is_ignored(self):
        exited = subprocess.Popen([sys.executable, "-c", "pass"])
        exited.wait()
        with TemporaryDirectory(prefix="oa-test-mp-stale-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            conversation_id = snapshot["state"]["conversation_id"]
            self.foreign_entry(directory, conversation_id, exited.pid, cancellable=True)
            async with conversations.conversation_operation(directory, conversation_id) as state:
                self.assertEqual(state["conversation_id"], conversation_id)
            self.assertNotIn(conversations._operation_key(directory, conversation_id), conversations._registry_read())

    async def test_stop_requests_cancel_in_other_process_and_waits_for_release(self):
        sleeper = _spawn_sleeper()
        try:
            with TemporaryDirectory(prefix="oa-test-mp-stop-") as temporary:
                directory = Path(temporary)
                snapshot = await conversations.create_conversation(directory)
                conversation_id = snapshot["state"]["conversation_id"]
                key = conversations._operation_key(directory, conversation_id)
                self.foreign_entry(directory, conversation_id, sleeper.pid, cancellable=True)
                observed = {}

                async def other_process_finishes():
                    # 模拟另一进程：看到取消请求后保存并注销登记。
                    while not conversations._registry_read().get(key, {}).get("cancel_requested"):
                        await asyncio.sleep(0.02)
                    observed["cancel_requested"] = True
                    await asyncio.sleep(0.3)
                    registry = conversations._registry_read()
                    del registry[key]
                    conversations._registry_write(registry)
                    observed["released_at"] = time.monotonic()

                finisher = asyncio.create_task(other_process_finishes())
                state = await conversations.stop_generation(directory, conversation_id)
                returned_at = time.monotonic()
                await finisher
                self.assertTrue(observed["cancel_requested"])
                self.assertGreaterEqual(returned_at, observed["released_at"], "须等待另一进程释放对话后再返回")
                self.assertEqual(state["conversation_id"], conversation_id)
        finally:
            sleeper.kill()
            sleeper.wait()

    async def test_stop_refuses_confirmed_operation_in_other_process(self):
        sleeper = _spawn_sleeper()
        try:
            with TemporaryDirectory(prefix="oa-test-mp-stop-confirmed-") as temporary:
                directory = Path(temporary)
                snapshot = await conversations.create_conversation(directory)
                conversation_id = snapshot["state"]["conversation_id"]
                self.foreign_entry(directory, conversation_id, sleeper.pid, cancellable=False)
                with self.assertRaises(HTTPException) as raised:
                    await conversations.stop_generation(directory, conversation_id)
                self.assertEqual(raised.exception.status_code, 409)
                entry = conversations._registry_read()[conversations._operation_key(directory, conversation_id)]
                self.assertFalse(entry["cancel_requested"], "不可中断的操作不得写入取消请求")
        finally:
            sleeper.kill()
            sleeper.wait()

    async def test_cancel_request_from_other_process_cancels_local_generation(self):
        with TemporaryDirectory(prefix="oa-test-mp-watch-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            conversation_id = snapshot["state"]["conversation_id"]
            key = conversations._operation_key(directory, conversation_id)
            started = asyncio.Event()

            async def generation():
                async with conversations.conversation_operation(directory, conversation_id, cancellable=True):
                    started.set()
                    await asyncio.sleep(30)

            task = asyncio.create_task(generation())
            await started.wait()
            self.assertIn(key, conversations._registry_read())
            # 另一进程处理“停止生成”时只写取消请求。
            registry = conversations._registry_read()
            registry[key]["cancel_requested"] = True
            conversations._registry_write(registry)
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)
            self.assertNotIn(key, conversations._registry_read(), "生成任务结束后注销登记")
            self.assertNotIn((directory, conversation_id), conversations._ACTIVE_OPERATIONS)

    async def test_local_stop_behaviour_is_unchanged(self):
        with TemporaryDirectory(prefix="oa-test-mp-local-stop-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            conversation_id = snapshot["state"]["conversation_id"]
            started = asyncio.Event()

            async def generation():
                async with conversations.conversation_operation(directory, conversation_id, cancellable=True):
                    started.set()
                    await asyncio.sleep(30)

            task = asyncio.create_task(generation())
            await started.wait()
            state = await conversations.stop_generation(directory, conversation_id)
            self.assertTrue(task.cancelled())
            self.assertEqual(state["conversation_id"], conversation_id)
            self.assertNotIn(conversations._operation_key(directory, conversation_id), conversations._registry_read())


class MemoryLockTest(IsolatedAsyncioTestCase):
    async def test_nested_memory_functions_do_not_deadlock(self):
        with TemporaryDirectory(prefix="oa-test-mp-memory-") as temporary:
            directory = Path(temporary)
            result = memory_graph.run_memory_pipeline(
                directory, 7, None, None, [{"role": "user", "content": "请记住我偏好使用简体中文回复"}],
                "请记住我偏好使用简体中文回复",
            )
            self.assertIn("summary", result)
            listed = memory_graph.list_memories(directory, 7)
            self.assertIsInstance(listed["items"], list)
            self.assertEqual(memory_graph._LOCK_DEPTH, {}, "退出后不残留嵌套计数")

    async def test_memory_lock_does_not_create_user_directory(self):
        with TemporaryDirectory(prefix="oa-test-mp-memory-dir-") as temporary:
            directory = Path(temporary) / "never-created"
            memory_graph.list_memories(directory, 7)
            self.assertFalse(directory.exists(), "只读查询不应创建用户目录")


class BackgroundLeaderTest(IsolatedAsyncioTestCase):
    async def test_non_postgresql_runs_loops_directly(self):
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        started = asyncio.Event()

        async def loop():
            started.set()
            await asyncio.sleep(30)

        leader = asyncio.create_task(process_coordination.run_background_leader(
            engine, lambda: [asyncio.create_task(loop())],
        ))
        await asyncio.wait_for(started.wait(), timeout=5)
        leader.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await leader
        await engine.dispose()
