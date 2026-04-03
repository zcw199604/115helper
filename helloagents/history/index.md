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
| 202604021030 | p115_open_upload | 功能 | ✅已完成 | [链接](2026-04/202604021030_p115_open_upload/) |
| 202604021120 | remote_leaf_precreate | 功能 | ✅已完成 | [链接](2026-04/202604021120_remote_leaf_precreate/) |
| 202604021155 | align_get_folder | 功能 | ✅已完成 | [链接](2026-04/202604021155_align_get_folder/) |
| 202604021245 | mobile_frontend | 功能 | ✅已完成 | [链接](2026-04/202604021245_mobile_frontend/) |
| 202604030040 | align_plugin_upload_flow | 重构 | ✅已完成 | [链接](2026-04/202604030040_align_plugin_upload_flow/) |
| 202604021330 | 115_upload_flow_compare | 文档 | ✅已完成 | [链接](2026-04/202604021330_115_upload_flow_compare/) |

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
- [202604021030_p115_open_upload](2026-04/202604021030_p115_open_upload/) - 对齐 plugin 风格的 115 Open 上传链路
- [202604021120_remote_leaf_precreate](2026-04/202604021120_remote_leaf_precreate/) - 对齐 plugin 的远端叶子目录预创建策略
- [202604021155_align_get_folder](2026-04/202604021155_align_get_folder/) - 对齐 plugin `_get_folder` 目录对象语义
- [202604021245_mobile_frontend](2026-04/202604021245_mobile_frontend/) - 增强前端移动端响应式兼容
- [202604030040_align_plugin_upload_flow](2026-04/202604030040_align_plugin_upload_flow/) - 将 115 上传主流程调整为插件对齐方式，并保留批处理缓存兼容模式
- [202604021330_115_upload_flow_compare](2026-04/202604021330_115_upload_flow_compare/) - 对比 115helper 与 MoviePilot-Plugins 的 115 上传目录创建与同步流程
