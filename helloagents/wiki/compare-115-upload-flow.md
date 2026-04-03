# 115 上传流程对比：115helper vs MoviePilot-Plugins

## 结论摘要
- **结论：不完全一致。** `115helper` 当前实现已经**部分对齐** MoviePilot-Plugins 的上传链路设计目标，但在“目录不存在时如何创建目录”“是否先列目录再逐级创建”“上传前是否先同步远端目录文件列表”这三点上，执行顺序与 API 选择仍然存在差异。
- **一致的部分**：两边都会在正式上传文件前先确保目标目录存在；文件上传都会优先尝试秒传，再在未命中时进入分片/Open 上传链路。
- **不一致的部分**：
  - `115helper` 的目录创建入口统一收敛为 `ensure_remote_dir()`，优先 `fs_dir_getid`，不存在时直接 `fs_makedirs_app(path, pid=0)` 递归建完整路径。
  - MoviePilot-Plugins 的“目录上传”主流程不是一次性递归建整条路径，而是先 `get_file_item()` 查父目录，不存在时再从根目录开始，**逐级 list → 查子目录 → create_folder**；若走 `P115Disk`，创建目录时核心 API 是 `fs_mkdir`；若走 `U115Open` 补丁，则可能是 `/open/folder/add` 或 `fs_mkdir`。
  - `115helper` 在目录就绪后，会按目录批次拉取/复用远端文件列表，再做防重与上传；MoviePilot-Plugins 的目录上传主流程里**没有同等的“先同步整个目标目录文件列表”步骤**，而是上传后再轮询 `get_file_item()` 确认结果。

## 对比范围
本次核对的代码范围如下：

### 115helper
- `backend/app/services/run_service.py`
- `backend/app/services/upload_strategy.py`
- `backend/app/integrations/p115/client.py`
- `backend/app/integrations/p115/open_uploader.py`

### MoviePilot-Plugins
- `plugins.v2/p115strmhelper/helper/monitor/__init__.py`
- `plugins.v2/p115disk/p115_api.py`
- `plugins.v2/p115strmhelper/core/p115disk.py`
- `plugins.v2/p115strmhelper/core/u115_open.py`
- `plugins.v2/p115strmhelper/patch/p115disk_upload.py`
- `plugins.v2/p115strmhelper/patch/u115_open.py`

## 一、115helper 当前执行顺序

### 1. 整体顺序
`run_service.py` 中，任务执行顺序是：
1. 扫描本地文件并按目标远端目录分组。
2. 对所有远端目录先执行 `precreate_remote_dirs()`，只预创建叶子目录。
3. 对每个远端目录执行 `prepare_dir_context()`：
   - 先 `_get_folder()` 确保目录存在。
   - 再读取远端目录文件列表（本地缓存命中则复用，否则调用 115 接口拉取）。
4. 对该目录下每个文件执行 `upload_candidate_in_context()`：
   - 可先按文件名/SHA1 做防重。
   - 再秒传初始化。
   - 秒传失败后再走分片上传。

### 2. 目录不存在时的处理
`upload_strategy.py` 中 `_get_folder()` 会统一调用 `gateway.ensure_remote_dir()`。

`client.py` 中 `ensure_remote_dir()` 的顺序是：
1. 如果路径是 `/`，直接返回根目录 ID `0`。
2. 先调用 `client.fs_dir_getid(path_str, app=False)` 查询整条路径对应目录 ID。
3. 如果查到 ID，直接返回。
4. 如果查不到或异常，则调用 `client.fs_makedirs_app(path_str, pid=0)` 一次性递归创建整条路径。
5. 返回创建后的 `cid`。

### 3. 上传前是否同步该目录内文件
**会。**
`prepare_dir_context()` 在目录确保存在后，会调用 `_get_remote_dir_items()`：
- 优先读进程内缓存；
- 若未开启强制刷新，则优先读本地 SQLite 远端目录缓存；
- 缓存未命中时调用 `gateway.list_remote_dir_files(pid)`；
- `list_remote_dir_files()` 底层调用 `client.fs_files({cid, limit, offset, show_dir: 0})` 拉取该目录全部文件。

这意味着 `115helper` 的顺序是：
**先建目录 → 再同步远端目录文件列表 → 再逐文件上传。**

### 4. 文件上传 API 顺序
#### 秒传阶段
- `client.upload_file_init(...)`

#### Open 上传阶段（启用 Open 凭证时）
- `POST /open/upload/init`
- 如触发二次校验：再次 `POST /open/upload/init`
- `GET /open/upload/get_token`
- `POST /open/upload/resume`
- OSS `init_multipart_upload`
- OSS `upload_part`
- OSS `complete_multipart_upload`

#### 回退分片上传阶段（未启用 Open 凭证时）
- `client.upload_file(...)`

## 二、MoviePilot-Plugins 当前执行顺序

## 1. 目录上传主流程
`p115strmhelper/helper/monitor/__init__.py` 中，目录上传逻辑顺序是：
1. 根据监控目录和相对路径计算 `target_file_path`。
2. 先调用 `storage_chain.get_file_item(storage, path=target_file_path.parent)` 直接查询目标父目录。
3. 如果父目录不存在：
   - 从根目录 `FileItem(storage=upload_storage, path="/")` 开始；
   - 对目标路径每一级目录：
     1. 先 `storage_chain.list_files(current_dir)` 列出当前目录下所有子项；
     2. 在返回结果里查找同名目录；
     3. 找不到再调用 `storage_chain.create_folder(current_dir, part)` 创建当前级目录；
     4. 成功后继续下一层。
4. 目录准备完成后，调用 `storage_chain.upload_file(target_fileitem, file_path, file_path.name)` 上传文件。
5. 上传完成后并不会先同步整个目录文件列表，而是最多重试 3 次，每次间隔递增，再通过 `storage_chain.get_file_item(path=target_file_path)` 轮询单文件是否已存在。

这意味着 MoviePilot-Plugins 的主流程是：
**先查父目录 → 不存在则逐级列目录/逐级建目录 → 直接上传文件 → 上传后轮询单文件是否出现。**

## 2. 目录不存在时的创建 API
这里要区分两层：

### 2.1 目录上传主流程所使用的标准存储接口
目录上传主流程调用的是 `storage_chain.create_folder()`，在 `p115disk` 里会转到 `P115Api.create_folder()`，其顺序是：
1. `get_pid_by_path(parent_path)` 获取父目录 ID。
2. `get_pid_by_path()` 内部会先查目录缓存；缓存未命中时交替调用：
   - `fs_dir_getid(path, app=False)`，或
   - `fs_dir_getid_app(path)`。
3. 若 `get_pid_by_path()` 发现路径不存在（`pid == 0`），会调用 `fs_makedirs_app(path, pid=0)` 递归创建该路径。
4. 拿到父目录 ID 后，`create_folder()` 再调用 `fs_mkdir({cname, pid})` 创建当前这一层目录。

所以在 MoviePilot-Plugins 的目录上传主路径里，**最终真正执行“当前级目录创建”的核心 API 是 `fs_mkdir`**；但在解析父目录 ID 时，又可能触发一次 `fs_makedirs_app` 作为兜底。

### 2.2 Open 补丁链路下的目录创建
如果启用了 `u115_open` 补丁，则 `create_folder()` 会改走 `U115OpenHelper.create_folder()`，该方法会随机选择：
- `POST /open/folder/add`，或
- `cookie_client.fs_mkdir(name, pid=...)`

并在目录已存在时按错误码返回现有目录。

因此 MoviePilot-Plugins 在“创建目录 API”这一点上本身就是**多分支实现**，并不是单一固定链路。

## 3. 文件上传 API 顺序
### 3.1 P115Disk 上传增强链路
`p115disk_upload.py` 会把上传改到 `P115DiskCore.upload()`，其核心顺序是：
1. `client.upload_file_init(...)`
2. 若命中秒传则直接完成。
3. 否则获取 OSS 上传凭证（通过 `self._p115_api._get_oss_token()`）
4. OSS `init_multipart_upload`
5. OSS `upload_part`
6. OSS `complete_multipart_upload`
7. 上传完成后调用 `self._p115_api.get_item(target_path)` 获取最终文件项。

### 3.2 U115Open 上传增强链路
若使用 `U115Open` 补丁，则文件上传顺序与 `115helper` 的 Open 上传链路高度相似：
1. `POST /open/upload/init`
2. 必要时再次 `POST /open/upload/init` 做二次校验
3. `GET /open/upload/get_token`
4. `POST /open/upload/resume`
5. OSS `init_multipart_upload`
6. OSS `upload_part`
7. OSS `complete_multipart_upload`
8. `get_item(target_path)` 延迟确认上传结果

## 三、逐项对比

| 对比项 | 115helper | MoviePilot-Plugins | 是否一致 |
|---|---|---|---|
| 目录不存在时的总体策略 | 统一入口 `_get_folder` / `ensure_remote_dir`，按完整路径一次性确保目录存在 | 主流程从根目录逐级 `list_files` + `create_folder` | ❌ 不一致 |
| 目录创建前是否先枚举父目录子项 | 不需要 | 需要，逐级 `list_files` 后再决定是否创建 | ❌ 不一致 |
| 目录创建核心 API | `fs_dir_getid` → `fs_makedirs_app` | 主路径多为 `fs_dir_getid/fs_dir_getid_app` + `fs_mkdir`；Open 补丁可走 `/open/folder/add` | ❌ 不一致 |
| 是否先预创建目录再处理文件 | 是，先收集叶子目录统一预创建 | 否，按单个目标文件路径边走边建 | ❌ 不一致 |
| 目录就绪后是否先同步该目录内文件列表 | 是，`fs_files` 拉全目录文件并写本地缓存 | 否，主流程直接上传，上传后仅轮询单文件 `get_file_item` | ❌ 不一致 |
| 秒传初始化 | `upload_file_init` | `upload_file_init` | ✅ 基本一致 |
| Open 上传链路 | `open/upload/init` → 二次校验 → `open/upload/get_token` → `open/upload/resume` → OSS 分片 | `U115Open` 分支同样如此 | ✅ 基本一致 |
| 非 Open 分片上传回退 | `client.upload_file(...)` | `P115DiskCore.upload()` 自己拿 OSS 凭证并分片 | ❌ 不一致 |

## 四、最终判断

### 1. 关于“目录不存在时创建文件夹”
**不一致。**
- `115helper`：偏“路径级一次性 ensure”。
- MoviePilot-Plugins：偏“从根目录逐级探测 + 当前级创建”。

### 2. 关于“同步该文件夹内文件”的执行顺序
**不一致。**
- `115helper`：先确保目录，再同步该目录文件列表，再上传该目录下文件。
- MoviePilot-Plugins：先确保目录，直接上传文件，上传后再轮询单文件结果；没有同层级的“先同步整个目录文件列表”步骤。

### 3. 关于“上传 API 调用顺序”
**部分一致。**
- 在**Open 上传链路**上，两边已经高度接近。
- 在**目录创建链路**和**非 Open 上传/目录同步策略**上，两边仍不一致。

## 五、如果你要的是“完全对齐 plugin”
建议后续对 `115helper` 再做两类决策中的一种：

### 方案 A：保持当前实现，只明确记录“设计性差异”
适合当前场景，因为：
- `115helper` 现有实现更适合批任务型同步；
- 先预创建叶子目录、再按目录批处理、再利用远端目录缓存，对大量文件同步更高效；
- 不需要为了“形式一致”退化成逐级 `list_files`。

### 方案 B：继续向 MoviePilot-Plugins 的目录上传流程完全对齐
如果你想做到字节级流程一致，可以继续改成：
1. 删除当前“叶子目录预创建 + 路径 ensure”主路径；
2. 改为按每个目标文件，从根目录逐级 `list_files` 查子目录；
3. 缺失时调用逐级 `create_folder`；
4. 上传后再轮询单文件存在性确认结果；
5. 将“目录缓存同步”从上传前批处理改成可选后处理。

但这样会牺牲当前 `115helper` 的批处理效率与目录级缓存优势。

## 六、简明回答
- **创建文件夹顺序是否一致？** 不一致。
- **同步该文件夹内文件的顺序是否一致？** 不一致。
- **上传 API 是否一致？** 只有 Open 上传主链路基本一致，目录创建 API 和非 Open 分片链路不一致。
