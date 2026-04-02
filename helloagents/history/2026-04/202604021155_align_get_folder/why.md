# 背景
当前目录创建行为已经接近 plugin，但仍主要通过 `resolve_remote_dir` 返回 ID，缺少与 plugin `_get_folder` 更一致的统一目录对象入口。

# 目标
将目录准备逻辑对齐为 `_get_folder` 风格：获取目录，不存在则创建，并复用目录对象缓存供预创建与批处理阶段共享。
