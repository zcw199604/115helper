"""数据库与 API 共享的枚举定义。"""

from enum import Enum


class UploadMode(str, Enum):
    """上传策略。"""

    FAST_ONLY = "fast_only"
    FAST_THEN_MULTIPART = "fast_then_multipart"
    MULTIPART_ONLY = "multipart_only"


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
