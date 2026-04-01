"""初始化 SQLite 数据库表结构。"""

from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成")
