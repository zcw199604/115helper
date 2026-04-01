# Changelog

本文件记录项目所有重要变更。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 初始化知识库与首个方案包，规划“本地目录同步到 115 网盘”的前后端项目。
- 初始化 FastAPI + Vue 3 前后端项目骨架。
- 新增 SQLite 数据模型、同步源 API、运行记录 API、系统设置 API。
- 新增本地目录扫描、后缀过滤、115 秒传/分片上传策略与 APScheduler 调度能力。
- 新增多任务管理、任务调度状态快照与任务级执行日志能力。
- 新增基于 SSE 的前端实时滚动日志能力。
- 新增手动执行/重试的后台异步运行能力。
- 新增检查点中断式取消能力。
- 新增单容器 Dockerfile，可在一个容器中同时托管后端 API 与前端静态资源。
- 移除开发态 docker-compose.yml，新增 GitHub Actions 自动构建并推送 Docker Hub 工作流。
- 新增数据库独立目录配置、远端目录文件 SQLite 缓存与任务级强制刷新远端目录配置。
- 优化任务执行为按远端目录批处理，并在按文件名防重模式下避免预先计算 SHA1。
- 新增基于 SSE 的前端实时滚动日志能力。
- 新增手动执行/重试的后台异步运行能力。
- 新增检查点中断式取消能力。
- 新增单容器 Dockerfile，可在一个容器中同时托管后端 API 与前端静态资源。
- 移除开发态 docker-compose.yml，新增 GitHub Actions 自动构建并推送 Docker Hub 工作流。
- 新增数据库独立目录配置、远端目录文件 SQLite 缓存与任务级强制刷新远端目录配置。
- 优化任务执行为按远端目录批处理，并在按文件名防重模式下避免预先计算 SHA1。
