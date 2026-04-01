"""任务日志实时流服务，负责按运行实例广播 SSE 事件。"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import defaultdict


class TaskLogStreamService:
    """按 run_id 管理日志订阅队列。"""

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def subscribe(self, run_id: int) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._subscribers[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: int, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(run_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(run_id, None)

    async def publish(self, run_id: int, event: str, payload: dict) -> None:
        data = self._format_sse(event, payload)
        async with self._lock:
            subscribers = list(self._subscribers.get(run_id, set()))
        for queue in subscribers:
            await queue.put(data)

    def publish_sync(self, run_id: int, event: str, payload: dict) -> None:
        asyncio.run_coroutine_threadsafe(self.publish(run_id, event, payload), self._loop)

    @staticmethod
    def _format_sse(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


task_log_stream_service = TaskLogStreamService()
