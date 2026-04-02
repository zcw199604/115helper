# 115helper

115helper 是一个面向 **115 网盘** 的本地部署同步控制台，适合在 NAS、Linux 服务器或个人主机中运行。

它提供一个统一的 Web 界面，用于管理“本地目录 → 115 网盘目录”的同步任务，并支持：

- 多同步任务管理
- 手动执行 / 定时执行
- 秒传 / 秒传失败回退 Open 分片上传 / 仅分片上传
- 后缀白名单过滤
- 排除规则过滤
- 远端防重模式：关闭 / 按文件名跳过 / 按 SHA1 跳过
- 远端目录文件缓存持久化到 SQLite
- 可选“强制同步远端目录文件”
- 后台异步执行
- 检查点中断式取消任务
- 运行记录、文件级结果、任务级日志、前端实时滚动日志
- 单容器部署

---

## 1. 项目结构

```text
backend/       FastAPI 后端、任务调度、同步引擎、SQLite 模型
frontend/      Vue 3 控制台
helloagents/   知识库、方案记录、历史归档
scripts/       本地开发辅助脚本
```

运行时推荐将数据拆分为两个宿主机目录：

```text
db/            SQLite 数据库目录
  └── app.db
data/          其它运行时数据目录
```

---

## 2. 当前主要能力

### 2.1 任务管理

- 创建多个同步任务
- 每个任务可独立配置：
  - 本地源目录
  - 115 目标目录
  - 上传模式
  - 后缀白名单
  - 排除规则
  - Cron 定时表达式
  - 是否启用任务
  - 远端防重模式
  - 是否强制同步远端目录文件

### 2.2 上传能力

支持三种上传模式：

- `fast_only`：仅秒传，未命中则跳过
- `fast_then_multipart`：秒传优先，失败后自动走 115 Open 分片上传
- `multipart_only`：仅分片上传；若配置了 Open 凭证则优先走 Open 分片链路

### 2.3 远端目录缓存

系统会把 115 目标目录中的文件信息缓存到本地 SQLite，用于减少重复请求 115 接口。

缓存相关行为：

- 默认优先使用本地 SQLite 中的远端目录缓存
- 同目录文件会按远端目录批次处理，同目录只做一次目录缓存装载/刷新
- 执行前会先收集所有远端叶子目录并预创建，行为对齐 plugin 的目录准备方式
- 目录准备已抽象为接近 plugin `_get_folder()` 的统一入口：获取目录，不存在则创建，并复用目录对象缓存
- 如果缓存不存在，会自动请求 115 并写入缓存
- 如果任务启用了“强制同步远端目录文件”，则每次执行前都会刷新目标目录缓存
- 上传成功后，新的远端文件信息也会回写到 SQLite 缓存中

### 2.4 远端防重模式

支持以下三种模式：

- `none`：关闭远端防重
- `name`：按文件名判断远端目录内是否已存在，命中则跳过（命中前不预先计算 SHA1）
- `sha1`：按 SHA1 判断远端目录内是否已存在，命中则跳过

命中跳过时，会写入任务日志与文件级记录。

### 2.5 运行与日志

- 手动执行 / 重试执行已改造成后台异步任务
- 运行详情页支持历史日志 + SSE 实时滚动日志
- 取消任务采用“检查点中断”策略，不会强杀线程，但会在安全点停止后续处理

---

## 3. 运行环境

### 后端

- Python 3.12
- FastAPI
- SQLAlchemy
- APScheduler
- p115client
- oss2（用于 115 Open 分片上传）

### 前端

- Node.js 20+ 或兼容版本
- Vue 3
- Vite
- Element Plus

### 数据存储

- SQLite

---

## 4. 环境变量

复制模板：

```bash
cp .env.example .env
```

示例：

```env
APP_ENV=development
P115_COOKIES=
# P115_COOKIES_FILE=/absolute/path/to/115-cookies.txt
P115_CHECK_FOR_RELOGIN=false
# 可选：配置后分片上传优先走 115 Open 上传链路
P115_OPEN_ACCESS_TOKEN=
P115_OPEN_REFRESH_TOKEN=
DEFAULT_PART_SIZE_MB=10
DEFAULT_MAX_WORKERS=1
DATA_DIR=/app/data
DB_DIR=/app/db
SQLITE_PATH=/app/db/app.db
```

### 关键参数说明

| 变量名 | 说明 |
|---|---|
| `P115_COOKIES` | 115 登录 Cookie 字符串，用于目录查询、目录创建与现有秒传能力 |
| `P115_COOKIES_FILE` | Cookie 文件路径，和 `P115_COOKIES` 二选一 |
| `P115_CHECK_FOR_RELOGIN` | 是否启用重新登录检查 |
| `P115_OPEN_ACCESS_TOKEN` | 可选，115 Open access token；通常可留空，由 refresh token 自动刷新 |
| `P115_OPEN_REFRESH_TOKEN` | 可选，配置后分片上传优先走 plugin 同款 115 Open 上传链路 |
| `DEFAULT_PART_SIZE_MB` | 默认分片大小（MB） |
| `DEFAULT_MAX_WORKERS` | 默认并发数 |
| `DATA_DIR` | 运行时数据目录 |
| `DB_DIR` | 数据库目录 |
| `SQLITE_PATH` | SQLite 文件路径，推荐 `/app/db/app.db` |

> 建议优先使用 `P115_COOKIES_FILE` 或 `--env-file`，不要把敏感 Cookie 直接硬编码到命令行历史里。

### Open 上传说明

- 当前服务已经支持 **plugin 风格的 115 Open 分片上传链路**：
  - `open/upload/init`
  - 二次校验（如命中）
  - `open/upload/get_token`
  - `open/upload/resume`
  - OSS 分片上传与合并
- 若未配置 `P115_OPEN_REFRESH_TOKEN` / `P115_OPEN_ACCESS_TOKEN`，系统会自动回退到原有 `p115client.upload_file` 分片上传。
- 为了尽量兼容现有部署，**秒传初始化仍保留 Cookie 链路**；Open 凭证主要影响普通分片上传路径。

---

## 5. 本地开发

### 5.1 安装后端依赖

```bash
uv sync --directory backend --python 3.12 --extra dev
```

### 5.2 启动后端

```bash
./scripts/dev-backend.sh
```

### 5.3 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5.4 运行测试

```bash
./scripts/test-backend.sh
```

---

## 6. Docker 部署

### 6.1 构建镜像

```bash
docker build -t 115helper:latest .
```

### 6.2 推荐宿主机目录

```text
/opt/115helper/
├── .env
├── db/
│   └── app.db
└── data/
```

### 6.3 运行容器

```bash
docker run -d \
  --name 115helper \
  -p 8000:8000 \
  --env-file /opt/115helper/.env \
  -v /opt/115helper/db:/app/db \
  -v /opt/115helper/data:/app/data \
  --restart unless-stopped \
  115helper:latest
```

### 6.4 为什么要分别挂载 `/app/db` 和 `/app/data`

- `/app/db`
  - 保存 SQLite 数据库
  - 包括：任务配置、运行记录、任务日志、远端目录缓存
- `/app/data`
  - 保存其它运行时数据

这样做的好处：

- 数据库便于单独备份
- 容器重建后任务配置不会丢失
- 远端目录缓存也会跟随数据库一起保留

### 6.5 访问地址

容器启动后：

- 前端界面：`http://<host>:8000/`
- API：`http://<host>:8000/api/v1/`
- 健康检查：`http://<host>:8000/healthz`

---

## 7. 首次使用建议

1. 先确认 115 Cookie 配置有效
2. 创建一个小范围测试任务
3. 先手动执行一次
4. 检查：
   - 任务是否创建成功
   - 运行记录是否生成
   - 实时日志是否正常显示
   - 115 目标目录是否正确创建
5. 确认无误后，再开启定时执行

---

## 8. 前端表单说明

### 后缀白名单

现在已经改为 **下拉多选**，不再要求手动输入。

常见预置项包括：

- `.mp4`
- `.mkv`
- `.avi`
- `.ts`
- `.m2ts`
- `.mov`
- `.wmv`
- `.flv`
- `.mpg`
- `.mpeg`
- `.iso`
- `.rmvb`
- `.srt`
- `.ass`
- `.ssa`
- `.sub`

未选择时表示不过滤后缀。

### 排除规则

现在也改为 **下拉多选**。

常见预置项包括：

- `sample*`
- `*.part`
- `*.tmp`
- `*.aria2`
- `*.torrent`
- `@eaDir/*`
- `.DS_Store`
- `Thumbs.db`
- `System Volume Information/*`
- `$RECYCLE.BIN/*`

规则按相对路径做通配匹配。

### 远端防重

可选：

- 关闭
- 按文件名跳过
- 按 SHA1 跳过

### 强制同步远端目录文件

- 关闭：优先使用本地 SQLite 缓存
- 开启：每次执行任务前都主动刷新 115 目标目录缓存

---

## 9. 数据持久化说明

### 9.1 SQLite 中保存了什么

数据库中会保存：

- 同步任务配置
- 运行记录
- 文件级同步结果
- 任务日志
- 远端目录缓存

### 9.2 为什么你会觉得“重启后配置丢了”

通常是以下原因之一：

- 没有挂载 `/app/db`
- 删除并重建了容器，但数据库仍在容器内部
- `SQLITE_PATH` 配置到了未挂载目录

### 9.3 正确做法

确保以下路径存在并挂载：

```bash
-v /opt/115helper/db:/app/db
-v /opt/115helper/data:/app/data
```

并确保：

```env
SQLITE_PATH=/app/db/app.db
```

---

## 10. 任务执行流程概览

```text
扫描本地目录
  -> 根据后缀白名单 / 排除规则筛选候选文件
  -> 确保远端目标目录存在（不存在则自动创建）
  -> 根据任务配置决定是否刷新远端目录缓存
  -> 按远端防重模式判断是否跳过
  -> 执行秒传 / 分片上传
  -> 写入文件记录、任务日志、运行记录
  -> 回写远端目录缓存
```

---

## 11. 日志与运行记录

### 任务日志

任务日志支持以下类型信息：

- 任务创建
- 扫描完成
- 缓存命中 / 缓存刷新
- 文件开始处理
- 文件跳过
- 秒传成功
- 分片上传成功
- 文件失败
- 任务结束

### 实时日志

运行详情页通过 SSE 获取实时日志：

- 页面先加载历史日志
- 再持续订阅新日志
- 任务结束后停止订阅

如果你部署在反向代理后，请确保支持 `text/event-stream` 长连接。

---

## 12. GitHub Actions

仓库已包含自动构建并推送 Docker Hub 的工作流：

- 文件：`.github/workflows/docker-image.yml`
- 触发方式：
  - push 到 `main`
  - 手动触发 `workflow_dispatch`

### 需要配置的 Secrets

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

### 可选 Variable

- `DOCKERHUB_IMAGE_NAME`
  - 例如：`yourname/115helper`

默认推送标签：

- `latest`
- `sha-<short_sha>`
- 手动触发时可指定自定义 tag

---

## 13. 已知限制

- 当前依赖 115 Cookie，不支持前端扫码登录
- 当前为单机部署设计，后台任务基于进程内线程池
- 取消任务为检查点中断，不是强杀线程
- 前端下拉多选目前使用预置候选项，尚不支持页面中动态新增自定义规则

---

## 14. 常用排查命令

### 查看容器日志

```bash
docker logs -f 115helper
```

### 查看数据库目录是否挂载成功

```bash
docker inspect 115helper
```

查看 `Mounts` 中是否包含：

- `/app/db`
- `/app/data`

### 查看宿主机数据库文件

```bash
ls -lah /opt/115helper/db
```

### 查看 SQLite 表

```bash
sqlite3 /opt/115helper/db/app.db ".tables"
```

---

## 15. 后续可扩展方向

- 前端支持自定义后缀与排除规则选项
- 远端目录缓存增加 TTL / 自动失效策略
- 更细粒度的远端冲突策略（如同名但大小不同继续上传）
- 多实例任务队列化
- 前端扫码登录 115

