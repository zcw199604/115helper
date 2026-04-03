# p115-gateway

## 目的
封装 p115client 与 115 网盘交互细节，降低业务层耦合。

## 模块概述
- **职责:** 客户端初始化、目录解析、目录创建、秒传初始化、Open 分片上传、错误标准化。
- **状态:** 🚧开发中
- **最后更新:** 2026-04-03

## 规范
- 已封装 `P115Client` 初始化、目录确保、逐级建目录、秒传初始化与远端目录列举能力。
- 普通上传优先走 plugin 同款 115 Open 上传链路：`open/upload/init` → 二次校验 → `open/upload/get_token` → `open/upload/resume` → OSS 分片上传。
- Open 上传过程支持日志回调与取消回调，便于与后台任务和实时日志机制集成。
- 远端目录准备已支持两种语义：`plugin_aligned` 模式按插件方式逐级探测/逐级创建目录；`batch_cached` 模式保留旧版批处理目录预创建能力。
- 若未配置 Open 凭证，普通上传会自动回退到 `p115client.upload_file`，避免影响旧部署。

## 近期补充
- 新增 `get_dir_id_by_path`、`find_child_dir`、`create_child_dir`、`ensure_remote_dir_plugin_style` 与 `get_remote_file_by_path` 封装，用于对齐插件式目录上传与上传后轮询确认。
- 新增同步源级 `upload_flow_mode`，允许在插件对齐模式与旧版批处理缓存模式之间切换。
- 新增 `wiki/compare-115-upload-flow.md`，系统对比 115helper 与 MoviePilot-Plugins 在目录创建、目录内文件同步顺序与上传 API 链路上的差异。
- 新增按目录批量列出 115 目标文件的能力，用于远端目录缓存刷新。
- 上传前的远端防重判断优先依赖本地 SQLite 缓存，必要时再调用 115 刷新目录。
- 新增 115 Open Access/Refresh Token 配置项，用于启用 plugin 风格 Open 上传。
