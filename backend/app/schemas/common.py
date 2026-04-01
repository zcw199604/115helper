"""公共响应结构。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应。"""

    code: int = 0
    message: str = "ok"
    data: T
