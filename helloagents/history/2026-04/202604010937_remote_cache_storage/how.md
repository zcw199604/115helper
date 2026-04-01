# 技术设计：数据库独立挂载与远端目录缓存持久化

## 方案概述
本方案在现有 FastAPI + SQLite 单机架构上做增量增强：
1. 将数据库文件路径从通用 `/app/data` 逻辑中抽离，增加独立数据库目录配置（例如 `/app/db/app.db`）。
2. 新增远端目录缓存表，按“任务目标目录 pid + 文件 id/名称/sha1/大小”等字段持久化 115 目录文件信息。
3. 任务执行时优先查询本地 SQLite 缓存；仅在缓存缺失、强制刷新开启或缓存过期时调用 115 接口重新拉取目录数据。
4. 在任务级别增加“强制同步远端目录文件”配置项，用于决定执行前是否强制刷新目标目录缓存。

## 数据模型变更
### 1. 同步任务表 `sync_sources`
新增字段：
- `force_refresh_remote_cache`：布尔/整数，表示执行任务时是否强制刷新远端目录缓存。

保留字段：
- `duplicate_check_mode`：`none | name | sha1`

### 2. 新增远端目录缓存表（建议名：`remote_dir_entries`）
核心字段建议：
- `id`
- `source_id`（可选，用于追踪来源任务；如需跨任务复用，可改为仅按 remote_dir_id 存储）
- `remote_dir_id`：115 目录 id（pid）
- `remote_dir_path`：规范化目录路径
- `remote_file_id`
- `remote_pickcode`
- `name`
- `sha1`
- `size`
- `is_dir`
- `fetched_at`
- 索引：
  - `(remote_dir_id, name)`
  - `(remote_dir_id, sha1)`
  - `(remote_dir_path)`

## 执行流程调整
### 现状
- `ensure_remote_dir` 获取目标目录 pid
- 通过 115 接口列出目录文件
- 在内存中做一次性目录缓存
- 任务结束后缓存失效

### 调整后
1. 根据任务目标目录与相对路径定位 remote dir。
2. 查询本地 SQLite 中的 `remote_dir_entries`。
3. 若命中且 `force_refresh_remote_cache=false`：
   - 直接用本地缓存执行按文件名/按 SHA1 防重判断。
4. 若未命中或 `force_refresh_remote_cache=true`：
   - 调用 115 接口批量拉取该目录文件列表。
   - 覆盖/刷新 `remote_dir_entries` 中该目录对应的数据。
   - 将刷新行为写入任务日志。
5. 完成防重判断后：
   - 命中跳过 → 记录日志
   - 未命中 → 继续秒传/分片上传
6. 上传成功后：
   - 追加/更新本地 `remote_dir_entries`，避免同一任务后续文件再次请求远端目录。

## 配置与部署调整
### 环境变量
新增或调整：
- `DATA_DIR`：一般运行时目录（保留）
- `DB_DIR` 或直接 `SQLITE_PATH=/app/db/app.db`

### Docker 挂载建议
- `/app/db`：单独挂载数据库
- `/app/data`：其它运行时文件

示例：
```bash
docker run -d \
  -v /opt/115helper/db:/app/db \
  -v /opt/115helper/data:/app/data \
  ...
```

## 前端调整
任务配置表单新增：
- `远端防重模式`（已有）
- `强制同步远端目录文件`（新增开关）

说明文案：
- 关闭：优先使用本地 SQLite 中的远端目录缓存
- 开启：任务执行前强制调用 115 接口刷新对应目标目录文件清单

## 日志与可观测性
新增日志场景：
- 使用本地远端目录缓存
- 强制刷新远端目录缓存
- 缓存未命中后自动拉取远端目录
- 刷新后缓存条目数
- 命中“按文件名/按 SHA1”跳过

## 风险与规避
### 风险1：缓存陈旧导致误判
- 通过 `force_refresh_remote_cache` 解决用户手动强刷场景。
- 未来可再引入 TTL 策略，本次先不强制。

### 风险2：SQLite 文件路径调整导致旧部署读取不到历史数据
- 提供兼容迁移与 README 升级说明。
- 默认可继续兼容旧 `SQLITE_PATH`，但推荐改为 `/app/db/app.db`。

### 风险3：同一远端目录被多个任务复用时缓存更新冲突
- 单机 SQLite + 顺序提交可满足当前需求。
- 表设计时按 `remote_dir_id` 做唯一维度覆盖刷新，减少重复。

## ADR
### ADR-20260401-01：将远端目录文件列表持久化到 SQLite
- **状态**：提议
- **原因**：减少重复调用 115 接口，提高任务执行性能，并为目录级防重提供持久化基础。
- **影响模块**：backend-api、sync-engine、p115-gateway、data

### ADR-20260401-02：数据库目录与运行时数据目录分离
- **状态**：提议
- **原因**：便于 Docker 挂载、备份与恢复，降低用户运维成本。
- **影响模块**：backend-api、deployment、documentation
