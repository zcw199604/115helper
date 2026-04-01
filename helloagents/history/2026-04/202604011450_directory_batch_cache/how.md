# 技术设计：目录级批处理远端缓存与防重性能优化

## 方案概述
本方案围绕“目录级批处理”对任务执行主流程做重构，而不是仅在上传策略内部做逐文件缓存判断。

核心思路：
1. 扫描本地候选文件后，先按**目标远端目录路径**分组。
2. 对每个目录批次：
   - 确保远端目录存在并获取 `pid`（一次）
   - 加载本地 SQLite 中该目录的缓存（一次）
   - 如果任务开启强制刷新，则远端拉取目录文件并覆盖缓存（一次）
3. 目录内逐文件处理时，共享这批目录上下文。
4. 当 `duplicate_check_mode=name` 时，优先按文件名从目录缓存判断；仅在未命中且需要真实上传时才计算 SHA1。
5. 当 `duplicate_check_mode=sha1` 时，目录内逐文件计算 SHA1 后与缓存匹配。

## 执行流程调整
### 现状
```text
for candidate in candidates:
  ensure_remote_dir()
  读取/刷新目录缓存
  计算 SHA1
  防重判断
  上传
```

### 目标流程
```text
scan_local_files()
按目标远端目录分组
for each remote_dir_group:
  ensure_remote_dir() 一次
  load/refresh remote_dir_cache 一次
  for each candidate in group:
    if mode == name:
      先按文件名判断
      命中 -> 跳过
      未命中 -> 需要上传时再算 SHA1
    elif mode == sha1:
      计算 SHA1
      按 SHA1 判断
    上传后回写目录缓存
```

## 代码改造点
### 1. `RunService.execute_run`
- 新增“候选文件 → 目标远端目录”分组逻辑。
- 在 `for candidate` 外层增加 `for remote_dir_group`。
- 目录级日志新增：
  - 目录开始处理
  - 命中本地缓存 / 远端刷新
  - 目录中文件数

### 2. `UploadStrategyService`
- 下沉为“已知目录上下文下的文件处理器”而不是每次自行解析目录。
- 支持接受：
  - `remote_dir_id`
  - `remote_dir_path`
  - `remote_items`
- 在 `name` 模式下：
  - 先匹配名称
  - 未命中时再计算 SHA1（仅在需要上传时）
- 在 `sha1` 模式下：
  - 才提前计算 SHA1

### 3. 目录缓存复用
- 当前 SQLite 缓存表继续保留。
- 新增运行时目录上下文对象，例如：
  - `RemoteDirContext(remote_dir_id, remote_dir_path, items)`
- 目录批次结束后无需额外落盘，上传成功时继续即时回写缓存。

## 日志设计
新增目录级日志，例如：
- `开始处理远端目录批次: /remote/Season 1，文件数 12`
- `命中本地远端目录缓存: /remote/Season 1，共 12 个文件`
- `强制同步远端目录文件完成: /remote/Season 1，共 12 个文件`
- `按文件名命中远端缓存，跳过: xxx.mkv`
- `按文件名未命中，进入上传流程: xxx.mkv`

## 性能收益点
### 收益1：避免逐文件目录初始化逻辑
同目录仅解析一次远端目录。

### 收益2：避免逐文件远端目录缓存读取
目录批次内只装载一次缓存。

### 收益3：按文件名模式延迟 SHA1 计算
对已存在的同名文件，直接跳过，不再完整读盘计算 SHA1。

## 风险与规避
### 风险1：目录分组逻辑与原相对路径映射不一致
- 规避：使用现有 `remote_root + relative_path.parent` 规则统一生成分组键。

### 风险2：目录上下文与上传后缓存回写顺序问题
- 规避：目录内文件处理后，立即更新内存目录缓存与 SQLite 缓存，确保同批次后续文件可见。

### 风险3：名称匹配导致误跳过
- 规避：仅在用户明确选择 `name` 模式时启用；保留 `sha1` 模式供精确校验场景使用。

## ADR
### ADR-20260401-03：任务执行按目标远端目录批处理
- **状态**：提议
- **原因**：降低同目录多文件场景下的重复目录处理开销，并提升远端缓存命中效率。
- **影响模块**：sync-engine、backend-api、p115-gateway

### ADR-20260401-04：按文件名模式采用延迟 SHA1 计算
- **状态**：提议
- **原因**：避免已命中的同名文件仍然完整读盘计算 SHA1，降低大文件场景耗时。
- **影响模块**：sync-engine、upload-strategy
