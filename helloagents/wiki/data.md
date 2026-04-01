# 数据模型

## 概述
首版采用 SQLite 存储配置、任务运行记录与文件同步状态，避免引入额外数据库依赖。

---

## 数据表/集合

### sync_sources

**描述:** 同步源配置。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | integer | 主键 | 主键 |
| name | text | 非空, 唯一 | 配置名称 |
| local_path | text | 非空 | 本地源目录 |
| remote_path | text | 非空 | 115 目标路径 |
| upload_mode | text | 非空 | 上传模式 |
| suffix_rules_json | text | 非空 | 后缀白名单 JSON |
| exclude_rules_json | text | 非空 | 排除规则 JSON |
| cron_expr | text | 可空 | 定时表达式 |
| enabled | integer | 非空 | 0/1 |
| created_at | datetime | 非空 | 创建时间 |
| updated_at | datetime | 非空 | 更新时间 |

**索引:**
- idx_sync_sources_enabled: enabled

### job_runs

**描述:** 每次任务运行的主记录。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | integer | 主键 | 主键 |
| source_id | integer | 非空, 外键 | 关联同步源 |
| trigger_type | text | 非空 | manual / cron / retry |
| status | text | 非空 | pending / running / success / partial_failed / failed / cancelled |
| started_at | datetime | 可空 | 开始时间 |
| finished_at | datetime | 可空 | 结束时间 |
| summary_json | text | 非空 | 统计摘要 JSON |
| error_message | text | 可空 | 全局错误信息 |

**索引:**
- idx_job_runs_source_id: source_id
- idx_job_runs_status: status

### file_records

**描述:** 文件级同步结果与去重缓存。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | integer | 主键 | 主键 |
| run_id | integer | 非空, 外键 | 关联运行记录 |
| source_id | integer | 非空, 外键 | 关联同步源 |
| relative_path | text | 非空 | 相对路径 |
| file_size | integer | 非空 | 文件大小 |
| file_sha1 | text | 可空 | 文件 SHA1 |
| suffix | text | 非空 | 文件后缀 |
| action | text | 非空 | skipped / fast_uploaded / multipart_uploaded / failed |
| remote_file_id | text | 可空 | 115 文件 ID |
| remote_pickcode | text | 可空 | 115 pickcode |
| message | text | 可空 | 结果说明 |
| synced_at | datetime | 非空 | 同步时间 |

**索引:**
- uniq_source_relative_path: source_id, relative_path
- idx_file_records_run_id: run_id
- idx_file_records_sha1: file_sha1

### task_logs

**描述:** 任务执行过程中的阶段日志。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | integer | 主键 | 主键 |
| run_id | integer | 非空, 外键 | 关联运行记录 |
| source_id | integer | 非空, 外键 | 关联同步任务 |
| level | text | 非空 | 日志级别 |
| stage | text | 非空 | 执行阶段 |
| message | text | 非空 | 日志内容 |
| created_at | datetime | 非空 | 记录时间 |

**索引:**
- idx_task_logs_run_id: run_id
- idx_task_logs_source_id: source_id

### app_settings

**描述:** 全局配置，例如 Cookie 文件位置、并发限制与默认上传行为。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| key | text | 主键 | 配置键 |
| value | text | 非空 | 配置值 |
| updated_at | datetime | 非空 | 更新时间 |
