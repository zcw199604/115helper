# 任务清单: 多任务同步与任务级日志增强

目录: `helloagents/plan/202603301147_multi_task_scheduler_logs/`

---

## 1. 数据模型与后端接口扩展
- [√] 1.1 在 `backend/app/models/` 中新增任务日志模型，并扩展运行/任务返回结构中的调度状态字段，验证 why.md#需求-r4-task-level-log-display-场景-structured-execution-log
- [√] 1.2 在 `backend/app/services/scheduler_service.py` 中补充任务调度状态快照能力（最近执行、下次执行、是否已注册），验证 why.md#需求-r2-independent-scheduling-场景-scheduler-visibility，依赖任务1.1
- [√] 1.3 在 `backend/app/api/` 中新增/调整任务列表、任务详情、任务启停、任务运行历史、运行日志查询接口，验证 why.md#需求-r1-multi-task-management-场景-task-overview，依赖任务1.2

## 2. 执行日志链路增强
- [√] 2.1 在 `backend/app/services/` 中新增任务日志写入服务，统一记录级别、阶段、消息与时间，验证 why.md#需求-r4-task-level-log-display-场景-structured-execution-log，依赖任务1.1
- [√] 2.2 在 `backend/app/services/run_service.py` 与 `sync_runner` 相关逻辑中接入任务级日志写入，覆盖开始、扫描、过滤、上传、完成、失败等阶段，验证 why.md#需求-r3-task-level-execution-record-场景-run-history-by-task，依赖任务2.1
- [√] 2.3 在 `backend/app/integrations/p115/` 中补充敏感信息脱敏与错误文案整理，验证 why.md#需求-r5-safe-logging-场景-sensitive-info-protection，依赖任务2.2

## 3. 前端任务管理与日志展示
- [√] 3.1 在 `frontend/src/types/` 与 `frontend/src/api/` 中新增任务列表、调度状态、日志查询类型与接口封装，验证 why.md#需求-r2-independent-scheduling-场景-scheduler-visibility，依赖任务1.3
- [√] 3.2 在 `frontend/src/views/sources/` 中将同步源列表升级为任务管理页，展示多个任务的源目录、目标目录、Cron、启用状态、最近执行与下次执行，验证 why.md#需求-r1-multi-task-management-场景-multiple-independent-tasks，依赖任务3.1
- [√] 3.3 在 `frontend/src/views/runs/` 中增强运行详情页，新增任务级日志列表/时间线展示，验证 why.md#需求-r4-task-level-log-display-场景-view-logs-in-ui，依赖任务3.1

## 4. 测试、文档与交付
- [√] 4.1 在 `backend/tests/` 中补充日志写入、任务调度状态和多任务查询测试，验证 why.md#需求-r3-task-level-execution-record-场景-latest-run-summary，依赖任务2.3
- [√] 4.2 在 `frontend/` 相关页面中验证多任务展示与日志视图构建通过，验证 why.md#需求-r4-task-level-log-display-场景-view-logs-in-ui，依赖任务3.3
- [√] 4.3 更新 `README.md` 与 `helloagents/wiki/*` 文档，补充“多任务同步 + 任务级日志”说明，验证 why.md#需求-r2-independent-scheduling-场景-per-task-cron，依赖任务4.1


## 执行总结
- 已完成多任务管理、独立调度状态快照与任务级日志链路增强。
- 已完成前端任务管理页与运行日志时间线展示。
- 已通过后端测试与前端构建验证。
