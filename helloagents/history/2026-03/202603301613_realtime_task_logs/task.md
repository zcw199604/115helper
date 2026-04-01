# 任务清单: 实时任务日志推送

目录: `helloagents/plan/202603301613_realtime_task_logs/`

---

## 1. 后端实时推送链路
- [√] 1.1 在 `backend/app/services/` 中新增日志流广播服务，按 `run_id` 管理订阅队列与连接清理，验证 why.md#需求-r1-realtime-log-stream-场景-subscribe-run-logs
- [√] 1.2 在 `backend/app/services/task_log_service.py` 中接入日志广播，确保新增日志写入数据库后同步推送，验证 why.md#需求-r2-historical--live-merge-场景-merge-without-duplicates，依赖任务1.1
- [√] 1.3 在 `backend/app/api/runs.py` 中新增 SSE 日志流接口，并补充结束状态/心跳事件，验证 why.md#需求-r1-realtime-log-stream-场景-auto-stop-on-finish，依赖任务1.2

## 2. 前端实时日志展示
- [√] 2.1 在 `frontend/src/api/` 中新增 SSE 订阅封装，支持连接、断开与事件回调，验证 why.md#需求-r3-resilient-connection-场景-temporary-disconnect，依赖任务1.3
- [√] 2.2 在 `frontend/src/views/runs/RunDetailView.vue` 中实现“历史日志 + 实时日志”合并、自动滚动、连接状态提示与去重逻辑，验证 why.md#需求-r2-historical--live-merge-场景-merge-without-duplicates，依赖任务2.1

## 3. 测试与文档
- [√] 3.1 在 `backend/tests/` 中补充广播与订阅相关测试，验证 why.md#需求-r1-realtime-log-stream-场景-subscribe-run-logs，依赖任务1.3
- [√] 3.2 更新 `README.md` 与 `helloagents/wiki/*`，补充实时日志说明、SSE 约束与使用方式，验证 why.md#需求-r3-resilient-connection-场景-temporary-disconnect，依赖任务3.1


## 执行总结
- 已完成基于 SSE 的任务日志实时推送链路。
- 已完成前端运行详情页的实时日志订阅、状态提示与自动滚动。
- 已通过后端测试与前端构建验证。
