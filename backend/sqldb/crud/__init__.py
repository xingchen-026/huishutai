"""sqldb.crud —— 数据库操作统一入口。

其它应用只从这里获取数据操作对象，不要直接写 ORM：

    from sqldb.crud import user_crud, user_info_crud, file_crud
    from sqldb.crud import llm_provider_crud, llm_model_crud
"""

from sqldb.crud.base import BaseCRUD, db_error_handler
from sqldb.crud.file import UploadedFileCRUD
from sqldb.crud.llm_model import LLMModelCRUD
from sqldb.crud.llm_provider import LLMProviderConfigCRUD
from sqldb.crud.user import UserCRUD
from sqldb.crud.user_info import UserInfoCRUD
from sqldb.crud.workflow import WorkflowCRUD
from sqldb.crud.workflow_edge import WorkflowEdgeCRUD
from sqldb.crud.workflow_event import WorkflowEventCRUD
from sqldb.crud.workflow_member import WorkflowMemberCRUD
from sqldb.crud.workflow_node import WorkflowNodeCRUD

user_crud = UserCRUD()
user_info_crud = UserInfoCRUD()
file_crud = UploadedFileCRUD()
llm_provider_crud = LLMProviderConfigCRUD()
llm_model_crud = LLMModelCRUD()
workflow_crud = WorkflowCRUD()
workflow_member_crud = WorkflowMemberCRUD()
workflow_node_crud = WorkflowNodeCRUD()
workflow_edge_crud = WorkflowEdgeCRUD()
workflow_event_crud = WorkflowEventCRUD()

__all__ = [
    "BaseCRUD",
    "db_error_handler",
    "UserCRUD",
    "UserInfoCRUD",
    "UploadedFileCRUD",
    "LLMProviderConfigCRUD",
    "LLMModelCRUD",
    "WorkflowCRUD",
    "WorkflowMemberCRUD",
    "WorkflowNodeCRUD",
    "WorkflowEdgeCRUD",
    "WorkflowEventCRUD",
    "user_crud",
    "user_info_crud",
    "file_crud",
    "llm_provider_crud",
    "llm_model_crud",
    "workflow_crud",
    "workflow_member_crud",
    "workflow_node_crud",
    "workflow_edge_crud",
    "workflow_event_crud",
]
