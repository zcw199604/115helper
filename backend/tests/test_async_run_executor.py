"""后台运行执行器测试。"""

from app.services.async_run_executor import AsyncRunExecutorService


def test_submit_run_deduplicates(monkeypatch):
    service = AsyncRunExecutorService()
    calls = []

    class DummyExecutor:
        def submit(self, fn, run_id):
            calls.append(run_id)
            return None

    service.executor = DummyExecutor()
    service.submit_run(1)
    service.submit_run(1)
    assert calls == [1]
