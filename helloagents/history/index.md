# 变更历史索引

本文件记录所有已完成变更的索引，便于追溯和查询。

---

## 索引

| 时间戳 | 功能名称 | 类型 | 状态 | 方案包路径 |
|--------|----------|------|------|------------|
| 202603300837 | 115_sync_console | 功能 | ✅已完成 | [链接](2026-03/202603300837_115_sync_console/) |
| 202603301147 | multi_task_scheduler_logs | 功能 | ✅已完成 | [链接](2026-03/202603301147_multi_task_scheduler_logs/) |
| 202603301613 | realtime_task_logs | 功能 | ✅已完成 | [链接](2026-03/202603301613_realtime_task_logs/) |
| 202603311642 | async_manual_runs | 功能 | ✅已完成 | [链接](2026-04/202603311642_async_manual_runs/) |
| 202604010202 | interruptible_runs | 功能 | ✅已完成 | [链接](2026-04/202604010202_interruptible_runs/) |
| 202604010937 | remote_cache_storage | 功能 | ✅已完成 | [链接](2026-04/202604010937_remote_cache_storage/) |
| 202604011450 | directory_batch_cache | 功能 | ✅已完成 | [链接](2026-04/202604011450_directory_batch_cache/) |

---

## 按月归档

### 2026-03
- [202603300837_115_sync_console](2026-03/202603300837_115_sync_console/) - 初始化 115 同步控制台前后端项目
- [202603301147_multi_task_scheduler_logs](2026-03/202603301147_multi_task_scheduler_logs/) - 增强多任务管理、调度状态与任务级日志
- [202603301613_realtime_task_logs](2026-03/202603301613_realtime_task_logs/) - 增强基于 SSE 的实时任务日志推送

### 2026-04
- [202603311642_async_manual_runs](2026-04/202603311642_async_manual_runs/) - 改造手动执行与重试为后台异步任务
- [202604010202_interruptible_runs](2026-04/202604010202_interruptible_runs/) - 增强检查点中断式取消能力
- [202604010937_remote_cache_storage](2026-04/202604010937_remote_cache_storage/) - 增强数据库独立挂载、远端目录缓存与任务级强制刷新能力
- [202604011450_directory_batch_cache](2026-04/202604011450_directory_batch_cache/) - 优化按目录批处理远端缓存与按文件名模式性能
