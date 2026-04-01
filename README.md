# 115helper

一个本地部署的 115 网盘同步控制台，提供：

- 本地目录 → 115 网盘同步
- 手动执行 / Cron 定时执行
- 仅秒传 / 秒传失败回退分片 / 仅分片上传
- 文件后缀过滤
- SQLite 持久化配置与运行记录
- 前后端分离控制台
- 不再内置任何前端 mock 数据，页面操作直接写入真实 SQLite

## 目录结构

- `backend/`：FastAPI 后端、SQLite、调度器、同步引擎
- `frontend/`：Vue 3 控制台
- `helloagents/`：知识库、方案包与历史记录
- `scripts/`：本地开发与测试脚本

## 快速开始

### 1. 配置环境变量

复制并编辑：

```bash
cp .env.example .env
```

至少配置：

- `P115_COOKIES` 或 `P115_COOKIES_FILE`
- `SQLITE_PATH`

### 2. 安装后端依赖并启动

```bash
uv sync --directory backend --python 3.12 --extra dev
./scripts/dev-backend.sh
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 运行后端测试

```bash
./scripts/test-backend.sh
```

### 5. 单容器 Docker 启动

先准备环境变量：

```bash
cp .env.example .env
```

构建镜像：

```bash
docker build -t 115helper:latest .
```

运行单容器：

```bash
docker run -d \
  --name 115helper \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  115helper:latest
```

说明：

- 任务配置、运行记录、日志默认保存在 `/app/data/app.db`
- 必须挂载 `-v $(pwd)/data:/app/data`，否则删除/重建容器后 SQLite 数据不会保留
- 如果你使用自定义 `SQLITE_PATH`，请确保它也位于持久化挂载目录中

启动后可直接访问：

- 前端界面: `http://localhost:8000/`
- 后端 API: `http://localhost:8000/api/v1/`
- 健康检查: `http://localhost:8000/healthz`


### 6. GitHub Actions 自动构建并推送 Docker Hub

仓库需要配置以下 Secrets：

- `DOCKERHUB_USERNAME`：Docker Hub 用户名
- `DOCKERHUB_TOKEN`：Docker Hub Access Token

可选配置以下 Repository Variable：

- `DOCKERHUB_IMAGE_NAME`：完整镜像名，例如 `yourname/115helper`

工作流文件：`.github/workflows/docker-image.yml`

触发方式：

- 推送到 `main` 分支时自动构建并推送
- 在 GitHub Actions 页面手动触发 `workflow_dispatch`

默认推送标签：

- `latest`（仅 main 分支）
- `sha-<short_sha>`
- 手动触发时可额外指定自定义 tag

## 当前实现范围

- 已初始化前后端工程骨架
- 已提供多同步任务管理、任务启停、任务运行历史、任务日志、系统设置 API
- 已提供本地文件扫描、后缀过滤、秒传/分片上传策略服务骨架
- 已提供前端多任务管理页、运行日志详情页面与实时滚动日志能力

## 后台异步任务说明

- 点击“立即执行”或“重试”后，接口会立即返回并在后台线程中继续运行。
- 运行详情页会先看到 `pending` 状态，随后进入 `running` 并持续接收实时日志。
- 当前采用进程内线程池执行，适合单机部署；未来如需多实例部署，建议迁移到独立任务队列。
- 当前取消采用“检查点中断”策略：不会强杀线程，但能阻止后续文件继续处理。

## 实时日志说明

- 运行详情页会先加载历史日志，再通过 SSE 订阅同一 `run_id` 的新增日志。
- 若任务已结束，页面会自动停止实时订阅。
- 若部署在反向代理之后，请确认代理允许 `text/event-stream` 长连接。

## 已知限制

- 手动执行与重试执行已改造成后台异步任务，接口会立即返回 run_id
- 取消任务现已支持检查点中断：已完成当前检查点后会停止后续文件处理
- 115 接口依赖本地 Cookie 与网络环境，建议先用小目录验证


## 实时日志

- 运行详情页会先加载历史日志，再通过 SSE 订阅新增日志。
- 若任务已结束，页面将停止实时订阅。
- 若部署在反向代理后，请确保代理支持 `text/event-stream` 长连接。
