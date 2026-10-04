"""控制台只读计算随客户端断开而取消，及时释放查询连接。"""

import asyncio

from fastapi import HTTPException, Request


async def _wait_for_disconnect(request: Request):
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return


async def run_dashboard_read(request: Request, calculation):
    worker = asyncio.create_task(calculation)
    disconnected = asyncio.create_task(_wait_for_disconnect(request))
    try:
        completed, _ = await asyncio.wait((worker, disconnected), return_when=asyncio.FIRST_COMPLETED)
        if worker in completed:
            return worker.result()
        disconnected.result()
        raise HTTPException(status_code=499, detail="客户端已取消控制台查询")
    finally:
        # 等待取消完成后再交还会话，避免 SQL 执行与连接回收并发。
        for task in (worker, disconnected):
            if not task.done():
                task.cancel()
        outcomes = await asyncio.gather(worker, disconnected, return_exceptions=True)
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                raise outcome
