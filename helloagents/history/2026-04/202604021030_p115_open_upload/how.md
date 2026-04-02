# 方案
1. 新增 Open 上传客户端，负责 access_token 刷新、Open API 请求、OSS 分片上传、二次校验与回调解析。
2. 调整现有 `P115Gateway.multipart_upload`，优先走 Open 上传；当缺少 Open 凭证时回退旧的 `p115client.upload_file`。
3. 为上传过程增加日志回调与取消回调，在分片循环中支持真正中断。
4. 更新环境变量示例、README 与知识库文档，说明 Open 上传配置方式与兼容行为。
