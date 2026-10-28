"""uploaded_file 表的数据操作（增删改查），不含业务逻辑。

文件本体不在这里：本文件只负责 PG 中文件元数据的读写。
MinIO 上传、签名 URL、大小/类型校验属于业务层（api.file_service）。
"""

from __future__ import annotations

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.models import UploadedFile
from sqldb.result import DBResult


class UploadedFileCRUD(BaseCRUD[UploadedFile]):
    """uploaded_file 表 CRUD。"""

    def __init__(self) -> None:
        super().__init__(UploadedFile)

    @db_error_handler
    def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> DBResult:
        """按用户分页查询文件记录（以后做“我的文件列表”可直接复用）。"""
        return self.get_list(
            {"user_id": user_id},
            order_by=("-created_at",),
            limit=limit,
            offset=offset,
        )