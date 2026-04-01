# 任务清单: 手动执行后台异步化

目录: `helloagents/plan/202603311642_async_manual_runs/`

---

## 1. 后端后台执行器
- [√] 1.1 在 `backend/app/services/` 中新增后台运行执行器，负责用独立数据库会话异步执行指定 `run_id`，验证 why.md#需求-r1-async-manual-trigger-场景-manual-trigger-returns-immediately
- [√] 1.2 调整 `backend/app/api/runs.py` 的手动执行与重试接口，使其创建运行记录后立即提交后台执行并返回，验证 why.md#需求-r2-async-retry-场景-retry-as-background-job，依赖任务1.1
- [√] 1.3 调整 `backend/app/services/scheduler_service.py` 使定时任务也尽量复用统一后台执行入口，验证 why.md#需求-r3-state-transition-visibility-场景-pending-to-running-to-finished，依赖任务1.1

## 2. 状态与并发保护增强
- [√] 2.1 在 `backend/app/services/run_service.py` 中收敛 `pending/running/finished/cancelled` 状态流转与并发保护逻辑，验证 why.md#需求-r4-concurrency-guard-场景-repeated-click，依赖任务1.2
- [√] 2.2 在 `backend/tests/` 中补充后台执行器、立即返回语义与并发保护测试，验证 why.md#需求-r1-async-manual-trigger-场景-manual-trigger-returns-immediately，依赖任务2.1

## 3. 前端交互与文档
- [√] 3.1 视需要调整 `frontend/` 的触发后跳转与状态提示，使其更符合后台异步任务语义，验证 why.md#需求-r3-state-transition-visibility-场景-pending-to-running-to-finished，依赖任务1.2
- [√] 3.2 更新 `README.md` 与 `helloagents/wiki/*` 文档，补充后台异步执行说明与约束，验证 why.md#需求-r2-async-retry-场景-retry-as-background-job，依赖任务2.2


## 执行总结
- 已完成手动执行与重试的后台异步化改造。
- 已统一后台执行入口，并保留实时日志与状态推送链路。
- 已通过后端测试与前端构建验证。
