# API 手册

## 概述
API 面向本地单用户控制台，默认部署在局域网或本机环境。所有接口返回统一结构：`{ code, message, data }`。

## 认证方式
首版默认不做复杂认证，部署层可通过反向代理 Basic Auth 或内网限制保护；如后续开放公网访问，再补充登录鉴权。

---

## 接口列表

### 同步源管理

#### [GET] /api/v1/tasks
**描述:** 获取同步源配置列表。

#### [POST] /api/v1/tasks
**描述:** 新建同步源。

**请求参数:**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 配置名称 |
| local_path | string | 是 | 本地目录绝对路径 |
| remote_path | string | 是 | 115 目标目录路径 |
| upload_mode | string | 是 | `fast_only` / `fast_then_multipart` / `multipart_only` |
| suffix_rules | string[] | 否 | 后缀白名单，如 `.mp4`, `.mkv` |
| exclude_rules | string[] | 否 | 排除模式 |
| cron_expr | string | 否 | Cron 表达式 |
| enabled | boolean | 是 | 是否启用 |

#### [PUT] /api/v1/tasks/{source_id}
**描述:** 更新同步源。

#### [POST] /api/v1/tasks/{source_id}/run
**描述:** 手动触发同步。

### 任务运行与日志

#### [GET] /api/v1/runs
**描述:** 获取运行记录列表。

#### [GET] /api/v1/runs/{run_id}
**描述:** 获取某次运行详情与文件级结果。

#### [POST] /api/v1/runs/{run_id}/retry
**描述:** 创建后台异步重试任务并立即返回。

#### [POST] /api/v1/runs/{run_id}/cancel
**描述:** 发出取消请求；若任务尚未启动则直接取消，若任务运行中则在检查点中断后续处理。

### 系统设置

#### [GET] /api/v1/settings
**描述:** 获取全局设置，例如 Cookie 存放状态、默认并发数、日志级别。

#### [PUT] /api/v1/settings
**描述:** 更新全局设置。


#### [GET] /api/v1/runs/{run_id}/logs
**描述:** 获取某次任务执行的阶段日志。

#### [GET] /api/v1/runs/{run_id}/logs/stream
**描述:** 通过 SSE 订阅某次任务执行的实时日志流。

#### [POST] /api/v1/tasks/{task_id}/toggle
**描述:** 启用或停用某个同步任务。


#### [GET] /api/v1/runs/{run_id}/logs/stream
**描述:** 通过 SSE 实时订阅某次运行的新增日志。
