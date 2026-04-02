# 方案
1. 在上传策略服务中新增 `RemoteDirInfo` 目录对象与 `_get_folder()` 统一入口。
2. 让 `resolve_remote_dir()`、叶子目录预创建与 `prepare_dir_context()` 统一复用 `_get_folder()`。
3. 更新 README、知识库与变更记录，说明目录准备已与 plugin `_get_folder` 语义对齐。
