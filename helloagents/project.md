# 项目技术约定

---

## 技术栈
- **后端:** Python 3.12 + FastAPI + SQLAlchemy + APScheduler
- **前端:** Vue 3 + Vite + TypeScript + Element Plus
- **数据:** SQLite（本地单机部署）
- **115 集成:** p115client（优先沿用本地插件已验证调用方式）

---

## 开发约定
- **代码规范:** 后端使用 Ruff + Black，前端使用 ESLint + Prettier。
- **命名约定:** Python 使用 snake_case；前端组件使用 PascalCase；数据库表名使用 snake_case 复数。
- **目录约定:** `backend/` 存放 API 与任务调度，`frontend/` 存放控制台界面，`data/` 存放 SQLite 与运行时文件。
- **容器化:** 根目录 `Dockerfile` 提供单容器构建，运行时由 FastAPI 托管前端静态资源。
- **CI/CD:** 使用 GitHub Actions 在 `main` 分支推送及手动触发时自动构建并推送 Docker Hub 镜像。

---

## 错误与日志
- **策略:** API 返回统一响应结构；同步任务错误按“任务级/文件级”分别记录。
- **日志:** 统一结构化日志，至少包含任务 ID、源目录 ID、文件路径、上传模式、耗时、结果状态。
- **审计:** Cookie/令牌类敏感信息禁止写入日志或前端响应。

---

## 测试与流程
- **测试:** 后端覆盖单元测试与核心同步流程集成测试；前端覆盖配置表单和任务列表关键交互。
- **提交:** 使用语义化提交前缀，例如 `feat:`、`fix:`、`docs:`。
- **发布:** 默认单机部署，后续优先提供 Docker Compose 方案。
