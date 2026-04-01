"""任务日志流服务测试。"""

import asyncio

from app.services.task_log_stream_service import TaskLogStreamService


def test_stream_service_publish_and_unsubscribe() -> None:
    async def runner():
        service = TaskLogStreamService()
        queue = await service.subscribe(1)
        await service.publish(1, 'log', {'id': 10, 'message': 'ok'})
        payload = await asyncio.wait_for(queue.get(), timeout=1)
        assert 'event: log' in payload
        assert '"id": 10' in payload
        await service.unsubscribe(1, queue)
        assert 1 not in service._subscribers

    asyncio.run(runner())
