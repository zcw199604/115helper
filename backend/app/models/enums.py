"""数据库与 API 共享的枚举定义。"""

from enum import Enum


class UploadMode(str, Enum):
    """上传策略。"""

    FAST_ONLY = "fast_only"
    FAST_THEN_MULTIPART = "fast_then_multipart"
    MULTIPART_ONLY = "multipart_only"


class UploadFlowMode(str, Enum):
    """同步流程模式。"""

    PLUGIN_ALIGNED = "plugin_aligned"
    BATCH_CACHED = "batch_cached"
    TMP_STAGE_THEN_MOVE = "tmp_stage_then_move"


class DuplicateCheckMode(str, Enum):
    """远端防重复匹配模式。"""

    NONE = "none"
    NAME = "name"
    SHA1 = "sha1"


class RunStatus(str, Enum):
    """任务运行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    """任务触发方式。"""

    MANUAL = "manual"
    CRON = "cron"
    RETRY = "retry"


class FileAction(str, Enum):
    """文件级处理动作。"""

    SKIPPED = "skipped"
    FAST_UPLOADED = "fast_uploaded"
    MULTIPART_UPLOADED = "multipart_uploaded"
    FAILED = "failed"
