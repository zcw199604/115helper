# 任务清单: 可中断后台任务执行

目录: `helloagents/plan/202604010202_interruptible_runs/`

---

## 1. 执行器取消能力增强
- [√] 1.1 在 `backend/app/services/async_run_executor.py` 中新增取消标记、运行上下文查询与清理逻辑，验证 why.md#需求-r1-cancel-signal-场景-cancel-running-run
- [√] 1.2 在 `backend/app/api/runs.py` 中增强取消接口，接入执行器取消信号，并区分 pending/running/已结束场景，验证 why.md#需求-r1-cancel-signal-场景-cancel-pending-run，依赖任务1.1

## 2. 运行服务中断检查点
- [√] 2.1 在 `backend/app/services/run_service.py` 中增加取消检查点，确保扫描后、逐文件处理前后都能停止后续处理，验证 why.md#需求-r2-interrupt-checkpoints-场景-stop-before-next-file，依赖任务1.1
- [√] 2.2 调整日志与 SSE 推送，使取消请求和真正中断都能被前端观察到，验证 why.md#需求-r3-consistent-visibility-场景-cancelled-with-logs，依赖任务2.1

## 3. 测试与文档
- [√] 3.1 在 `backend/tests/` 中补充 pending/running 取消和上下文清理测试，验证 why.md#需求-r1-cancel-signal-场景-cancel-running-run，依赖任务2.2
- [√] 3.2 更新 `README.md` 与 `helloagents/wiki/*`，补充“检查点中断式取消”说明与限制，验证 why.md#需求-r2-interrupt-checkpoints-场景-stop-before-next-file，依赖任务3.1


## 执行总结
- 已完成执行器取消信号与运行服务检查点中断机制。
- 已实现 pending/running 场景下的取消一致性与日志/SSE 联动。
- 已通过后端测试验证。
