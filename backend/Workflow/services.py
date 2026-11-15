"""Workflow 业务层：工作流/成员/节点/连线/事件/导入导出/执行。"""

from __future__ import annotations

import uuid
from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from sqldb.crud import (
    user_crud,
    workflow_crud,
    workflow_edge_crud,
    workflow_event_crud,
    workflow_member_crud,
    workflow_node_crud,
)
from sqldb.enums import DBStatus
from Workflow import executor
from Workflow.node.base import NodeError
from Workflow.node_loader import get_node_meta, list_node_files
from Workflow.result import WFResult, WFStatus

_EDIT_ROLES = {"owner", "editor"}
_DB_TO_WF = {
    DBStatus.SUCCESS: WFStatus.SUCCESS,
    DBStatus.NOT_FOUND: WFStatus.NOT_FOUND,
    DBStatus.DUPLICATE_ERR: WFStatus.PARAM_ERR,
    DBStatus.PARAM_ERR: WFStatus.PARAM_ERR,
    DBStatus.CONFLICT: WFStatus.CONFLICT,
    DBStatus.SERVICE_ERR: WFStatus.UNKNOWN_ERR,
    DBStatus.UNKNOWN_ERR: WFStatus.UNKNOWN_ERR,
}


def _from_db(result, message: str | None = None) -> WFResult:
    return WFResult(
        _DB_TO_WF.get(result.code, WFStatus.UNKNOWN_ERR),
        message or result.message,
        None,
    )


def _iso(value):
    return value.isoformat() if value else None


# ==================== 序列化 ====================
def _workflow_dict(workflow, role: str, node_count: int | None = None) -> dict:
    return {
        "id": workflow.pk,
        "name": workflow.name,
        "description": workflow.description,
        "owner_id": workflow.owner_id,
        "owner_name": workflow.owner.username if workflow.owner_id else "",
        "role": role,
        "node_count": node_count,
        "created_at": _iso(workflow.created_at),
        "updated_at": _iso(workflow.updated_at),
    }


def _node_dict(node) -> dict:
    return {
        "key": node.key,
        "node_type": node.node_type,
        "name": node.name,
        "position": {"x": node.position_x, "y": node.position_y},
        "config": node.config or {},
        "version": node.version,
        "created_at": _iso(node.created_at),
        "updated_at": _iso(node.updated_at),
    }


def _relation_dict(edge) -> dict:
    return {
        "id": edge.pk,
        "source_key": edge.source_key,
        "source_port": edge.source_port,
        "target_key": edge.target_key,
        "target_port": edge.target_port,
        "created_at": _iso(edge.created_at),
    }


def _member_dict(user, role: str, created_at=None) -> dict:
    return {
        "user_id": user.pk,
        "username": user.username,
        "role": role,
        "created_at": _iso(created_at),
    }


def _event_dict(event) -> dict:
    return {
        "id": event.pk,
        "op": event.op,
        "payload": event.payload or {},
        "actor_id": event.actor_id,
        "actor_name": event.actor.username if event.actor_id and event.actor else "",
        "created_at": _iso(event.created_at),
    }


# ==================== 访问控制 / 事件 ====================
def _role_for(workflow, user) -> str | None:
    if workflow.owner_id == user.pk:
        return "owner"
    result = workflow_member_crud.get_by_workflow_user(workflow.pk, user.pk)
    if result.code == DBStatus.SUCCESS:
        return result.data.role
    return None


def _access(user, workflow_id: int, *, edit: bool = False):
    result = workflow_crud.get_by_pk(workflow_id)
    if result.code == DBStatus.NOT_FOUND:
        return None, None, WFResult(WFStatus.NOT_FOUND, "工作流不存在")
    if result.code != DBStatus.SUCCESS:
        return None, None, _from_db(result)

    workflow = result.data
    role = _role_for(workflow, user)
    if role is None:
        return None, None, WFResult(WFStatus.FORBIDDEN, "无权访问该工作流")
    if edit and role not in _EDIT_ROLES:
        return None, role, WFResult(WFStatus.FORBIDDEN, "只读成员不能修改工作流")
    return workflow, role, None


def _record_event(workflow, user, op: str, payload: dict | None = None):
    workflow_event_crud.create(workflow=workflow, actor=user, op=op, payload=payload or {})
    workflow_crud.update(workflow.pk, updated_at=timezone.now())


def _members(workflow) -> list[dict]:
    items = [_member_dict(workflow.owner, "owner", workflow.created_at)]
    result = workflow_member_crud.list_by_workflow(workflow.pk)
    if result.code == DBStatus.SUCCESS:
        for member in result.data:
            items.append(_member_dict(member.user, member.role, member.created_at))
    return items


def _state(workflow, role: str) -> WFResult:
    nodes_result = workflow_node_crud.list_by_workflow(workflow.pk)
    edges_result = workflow_edge_crud.list_by_workflow(workflow.pk)
    if nodes_result.code != DBStatus.SUCCESS:
        return _from_db(nodes_result)
    if edges_result.code != DBStatus.SUCCESS:
        return _from_db(edges_result)

    latest = workflow_event_crud.latest_id(workflow.pk)
    return WFResult(
        WFStatus.SUCCESS,
        "ok",
        {
            "workflow": _workflow_dict(workflow, role, len(nodes_result.data)),
            "nodes": [_node_dict(node) for node in nodes_result.data],
            "relations": [_relation_dict(edge) for edge in edges_result.data],
            "members": _members(workflow),
            "last_event_seq": latest.data if latest.code == DBStatus.SUCCESS else 0,
            "node_types": list_node_files(),
        },
    )


# ==================== 工作流 ====================
def list_workflows(user) -> WFResult:
    result = workflow_crud.list_for_user(user.pk)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result)

    items = []
    for workflow in result.data:
        role = _role_for(workflow, user)
        if role is None:
            continue
        count = workflow_node_crud.count(workflow_id=workflow.pk)
        items.append(
            _workflow_dict(workflow, role, count.data if count.code == DBStatus.SUCCESS else 0)
        )
    return WFResult(WFStatus.SUCCESS, "ok", {"total": len(items), "workflows": items})


def create_workflow(user, data: dict | None = None) -> WFResult:
    data = data or {}
    name = str(data.get("name") or "").strip()[:100]
    if not name:
        return WFResult(WFStatus.PARAM_ERR, "工作流名称不能为空")
    description = str(data.get("description") or "").strip()[:500]

    created = workflow_crud.create(owner=user, name=name, description=description)
    if created.code != DBStatus.SUCCESS:
        return _from_db(created)
    workflow = created.data
    _record_event(workflow, user, "workflow_created", {"name": name})
    return WFResult(
        WFStatus.SUCCESS,
        "工作流已创建",
        {"workflow": _workflow_dict(workflow, "owner", 0)},
    )


def get_workflow(user, workflow_id: int) -> WFResult:
    workflow, role, error = _access(user, workflow_id)
    if error:
        return error
    return _state(workflow, role)


def update_workflow(user, workflow_id: int, data: dict | None = None) -> WFResult:
    workflow, role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    data = data or {}
    fields = {}
    if "name" in data:
        name = str(data.get("name") or "").strip()[:100]
        if not name:
            return WFResult(WFStatus.PARAM_ERR, "工作流名称不能为空")
        fields["name"] = name
    if "description" in data:
        fields["description"] = str(data.get("description") or "").strip()[:500]
    if not fields:
        return WFResult(WFStatus.PARAM_ERR, "没有需要更新的字段")

    updated = workflow_crud.update(workflow.pk, **fields)
    if updated.code != DBStatus.SUCCESS:
        return _from_db(updated)
    workflow = updated.data
    _record_event(workflow, user, "workflow_updated", fields)
    return WFResult(
        WFStatus.SUCCESS,
        "工作流已更新",
        {"workflow": _workflow_dict(workflow, role, None)},
    )


def delete_workflow(user, workflow_id: int) -> WFResult:
    workflow, role, error = _access(user, workflow_id, edit=True)
    if error:
        return error
    if role != "owner":
        return WFResult(WFStatus.FORBIDDEN, "只有创建者可以删除工作流")
    result = workflow_crud.delete(workflow.pk)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result)
    return WFResult(WFStatus.SUCCESS, "工作流已删除", {"id": workflow_id})


# ==================== 成员 ====================
def add_member(user, workflow_id: int, data: dict | None = None) -> WFResult:
    workflow, role, error = _access(user, workflow_id, edit=True)
    if error:
        return error
    if role != "owner":
        return WFResult(WFStatus.FORBIDDEN, "只有创建者可以邀请成员")

    data = data or {}
    username = str(data.get("username") or "").strip()
    role_value = str(data.get("role") or "editor").strip()
    if role_value not in {"editor", "viewer"}:
        return WFResult(WFStatus.PARAM_ERR, "角色只能是 editor 或 viewer")

    found = user_crud.get(username=username)
    if found.code != DBStatus.SUCCESS:
        return WFResult(WFStatus.NOT_FOUND, "用户不存在")
    member_user = found.data
    if member_user.pk == workflow.owner_id:
        return WFResult(WFStatus.PARAM_ERR, "不能把创建者添加为协作者")

    created = workflow_member_crud.create(workflow=workflow, user=member_user, role=role_value)
    if created.code != DBStatus.SUCCESS:
        return _from_db(created, "该用户已是协作者")
    _record_event(
        workflow,
        user,
        "members_changed",
        {"added": member_user.username, "role": role_value},
    )
    return WFResult(WFStatus.SUCCESS, "已添加协作者", {"members": _members(workflow)})


def remove_member(user, workflow_id: int, member_user_id: int) -> WFResult:
    workflow, role, error = _access(user, workflow_id, edit=True)
    if error:
        return error
    if role != "owner":
        return WFResult(WFStatus.FORBIDDEN, "只有创建者可以移除成员")
    result = workflow_member_crud.delete_by_workflow_user(workflow_id, member_user_id)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result, "成员不存在")
    _record_event(workflow, user, "members_changed", {"removed_user_id": member_user_id})
    return WFResult(WFStatus.SUCCESS, "已移除协作者", {"members": _members(workflow)})


# ==================== 节点 ====================
def _position(data: dict) -> tuple[float, float] | None:
    if "position" not in data or data.get("position") is None:
        return 0.0, 0.0
    position = data.get("position")
    if not isinstance(position, dict):
        return None
    try:
        return float(position.get("x") or 0), float(position.get("y") or 0)
    except (TypeError, ValueError):
        return None


def add_node(user, workflow_id: int, data: dict | None = None) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    data = data or {}
    node_type = str(data.get("node_type") or "").strip()
    try:
        meta = get_node_meta(node_type)
    except NodeError as exc:
        return WFResult(WFStatus.PARAM_ERR, str(exc))

    position = _position(data)
    if position is None:
        return WFResult(WFStatus.PARAM_ERR, "position 必须是 {x, y} 对象")
    config = data.get("config")
    if config is None:
        config = {}
    if not isinstance(config, dict):
        return WFResult(WFStatus.PARAM_ERR, "config 必须是 JSON 对象")
    name = str(data.get("name") or meta.get("name") or node_type).strip()[:100]

    created = workflow_node_crud.create(
        workflow=workflow,
        key=uuid.uuid4().hex,
        node_type=node_type,
        name=name,
        position_x=position[0],
        position_y=position[1],
        config=config,
        version=1,
    )
    if created.code != DBStatus.SUCCESS:
        return _from_db(created)
    node = created.data
    _record_event(workflow, user, "node_added", {"node": _node_dict(node)})
    return WFResult(WFStatus.SUCCESS, "节点已添加", {"node": _node_dict(node)})


def update_node(user, workflow_id: int, node_key: str, data: dict | None = None) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    found = workflow_node_crud.get_by_key(workflow_id, node_key)
    if found.code != DBStatus.SUCCESS:
        return _from_db(found, "节点不存在")
    node = found.data

    data = data or {}
    base_version = data.get("base_version")
    if isinstance(base_version, bool) or not isinstance(base_version, int):
        return WFResult(WFStatus.PARAM_ERR, "base_version 必须是整数")

    fields = {}
    if "name" in data:
        name = str(data.get("name") or "").strip()[:100]
        if not name:
            return WFResult(WFStatus.PARAM_ERR, "节点名称不能为空")
        fields["name"] = name
    if "position" in data:
        position = _position(data)
        if position is None:
            return WFResult(WFStatus.PARAM_ERR, "position 必须是 {x, y} 对象")
        fields["position_x"] = position[0]
        fields["position_y"] = position[1]
    if "config" in data:
        if not isinstance(data["config"], dict):
            return WFResult(WFStatus.PARAM_ERR, "config 必须是 JSON 对象")
        fields["config"] = data["config"]
    if not fields:
        return WFResult(WFStatus.PARAM_ERR, "没有需要更新的字段")

    updated = workflow_node_crud.update_if_version(workflow_id, node_key, base_version, **fields)
    if updated.code == DBStatus.CONFLICT:
        return WFResult(WFStatus.CONFLICT, "节点已被其他人修改，请刷新后重试")
    if updated.code != DBStatus.SUCCESS:
        return _from_db(updated)
    node = updated.data
    _record_event(workflow, user, "node_updated", {"node": _node_dict(node)})
    return WFResult(WFStatus.SUCCESS, "节点已更新", {"node": _node_dict(node)})


def delete_node(user, workflow_id: int, node_key: str) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    found = workflow_node_crud.get_by_key(workflow_id, node_key)
    if found.code != DBStatus.SUCCESS:
        return _from_db(found, "节点不存在")

    workflow_edge_crud.delete_by_node_key(workflow_id, node_key)
    deleted = workflow_node_crud.delete(found.data.pk)
    if deleted.code != DBStatus.SUCCESS:
        return _from_db(deleted)
    _record_event(workflow, user, "node_deleted", {"key": node_key})
    return WFResult(WFStatus.SUCCESS, "节点已删除", {"key": node_key})


# ==================== 连线 ====================
def _would_create_cycle(workflow_id: int, source_key: str, target_key: str) -> bool:
    result = workflow_edge_crud.list_by_workflow(workflow_id)
    if result.code != DBStatus.SUCCESS:
        return True
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in result.data:
        graph[edge.source_key].append(edge.target_key)

    stack = [target_key]
    seen: set[str] = set()
    while stack:
        key = stack.pop()
        if key == source_key:
            return True
        if key in seen:
            continue
        seen.add(key)
        stack.extend(graph.get(key, []))
    return False


def _validate_import_graph(prepared_nodes: list[dict], prepared_edges: list[dict]) -> None:
    """导入时校验：单 start、端口合法、无环；空图允许用于清空画布。"""
    if not prepared_nodes:
        return
    if sum(1 for node in prepared_nodes if node["node_type"] == "start") != 1:
        raise _ImportError("工作流必须且只能有一个 start 节点")

    meta_by_key = {node["key"]: get_node_meta(node["node_type"]) for node in prepared_nodes}
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in prepared_edges:
        source_meta = meta_by_key[edge["source_key"]]
        target_meta = meta_by_key[edge["target_key"]]
        output_ids = {port.get("id") for port in source_meta.get("outputs", [])}
        input_ids = {port.get("id") for port in target_meta.get("inputs", [])}
        if edge["source_port"] not in output_ids:
            raise _ImportError(f"源端口不存在：{edge['source_port']}")
        if edge["target_port"] not in input_ids:
            raise _ImportError(f"目标端口不存在：{edge['target_port']}")
        graph[edge["source_key"]].append(edge["target_key"])

    state: dict[str, int] = {}

    def visit(key: str) -> None:
        current = state.get(key, 0)
        if current == 1:
            raise _ImportError("导入的连线不能形成环")
        if current == 2:
            return
        state[key] = 1
        for next_key in graph.get(key, []):
            visit(next_key)
        state[key] = 2

    for key in meta_by_key:
        visit(key)


def add_relation(user, workflow_id: int, data: dict | None = None) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    data = data or {}
    source_key = str(data.get("source_key") or "").strip()
    target_key = str(data.get("target_key") or "").strip()
    source_port = str(data.get("source_port") or "out").strip()[:64]
    target_port = str(data.get("target_port") or "in").strip()[:64]
    if not source_key or not target_key:
        return WFResult(WFStatus.PARAM_ERR, "source_key / target_key 不能为空")
    if source_key == target_key:
        return WFResult(WFStatus.PARAM_ERR, "不能把节点连接到自身")

    source = workflow_node_crud.get_by_key(workflow_id, source_key)
    target = workflow_node_crud.get_by_key(workflow_id, target_key)
    if source.code != DBStatus.SUCCESS or target.code != DBStatus.SUCCESS:
        return WFResult(WFStatus.NOT_FOUND, "节点不存在")

    try:
        source_meta = get_node_meta(source.data.node_type)
        target_meta = get_node_meta(target.data.node_type)
    except NodeError as exc:
        return WFResult(WFStatus.PARAM_ERR, str(exc))
    output_ids = {port.get("id") for port in source_meta.get("outputs", [])}
    input_ids = {port.get("id") for port in target_meta.get("inputs", [])}
    if source_port not in output_ids:
        return WFResult(WFStatus.PARAM_ERR, f"源端口不存在：{source_port}")
    if target_port not in input_ids:
        return WFResult(WFStatus.PARAM_ERR, f"目标端口不存在：{target_port}")

    if _would_create_cycle(workflow_id, source_key, target_key):
        return WFResult(WFStatus.PARAM_ERR, "不允许形成环")

    created = workflow_edge_crud.create(
        workflow=workflow,
        source_key=source_key,
        source_port=source_port,
        target_key=target_key,
        target_port=target_port,
    )
    if created.code != DBStatus.SUCCESS:
        return _from_db(created, "该连线已存在")
    _record_event(
        workflow,
        user,
        "edge_added",
        {"relation": _relation_dict(created.data)},
    )
    return WFResult(WFStatus.SUCCESS, "连线已添加", {"relation": _relation_dict(created.data)})


def delete_relation(user, workflow_id: int, edge_id: int) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    found = workflow_edge_crud.get_by_pk(edge_id)
    if found.code != DBStatus.SUCCESS or found.data.workflow_id != workflow_id:
        return WFResult(WFStatus.NOT_FOUND, "连线不存在")
    deleted = workflow_edge_crud.delete(edge_id)
    if deleted.code != DBStatus.SUCCESS:
        return _from_db(deleted)
    _record_event(workflow, user, "edge_deleted", {"id": edge_id})
    return WFResult(WFStatus.SUCCESS, "连线已删除", {"id": edge_id})


# ==================== 事件 / 节点目录 ====================
def list_events(user, workflow_id: int, after: int = 0, limit: int = 100) -> WFResult:
    workflow, _role, error = _access(user, workflow_id)
    if error:
        return error
    result = workflow_event_crud.list_after(workflow.pk, after, limit)
    if result.code != DBStatus.SUCCESS:
        return _from_db(result)
    latest = workflow_event_crud.latest_id(workflow.pk)
    return WFResult(
        WFStatus.SUCCESS,
        "ok",
        {
            "events": [_event_dict(event) for event in result.data],
            "last_event_seq": latest.data if latest.code == DBStatus.SUCCESS else 0,
        },
    )


def list_node_types() -> WFResult:
    return WFResult(WFStatus.SUCCESS, "ok", {"types": list_node_files()})


def get_node_type_meta(node_type: str) -> WFResult:
    try:
        meta = get_node_meta(node_type)
    except NodeError as exc:
        return WFResult(WFStatus.NOT_FOUND, str(exc))
    except Exception:  # noqa: BLE001
        return WFResult(WFStatus.NODE_LOAD_ERROR, "节点加载失败")
    return WFResult(WFStatus.SUCCESS, "ok", {"meta": meta})


# ==================== 导入 / 导出 ====================
def export_workflow(user, workflow_id: int) -> WFResult:
    workflow, _role, error = _access(user, workflow_id)
    if error:
        return error
    nodes_result = workflow_node_crud.list_by_workflow(workflow.pk)
    edges_result = workflow_edge_crud.list_by_workflow(workflow.pk)
    if nodes_result.code != DBStatus.SUCCESS:
        return _from_db(nodes_result)
    if edges_result.code != DBStatus.SUCCESS:
        return _from_db(edges_result)

    document = {
        "format": "huishutai.workflow",
        "format_version": 1,
        "name": workflow.name,
        "description": workflow.description,
        "nodes": [
            {
                "key": node.key,
                "type": node.node_type,
                "name": node.name,
                "position": {"x": node.position_x, "y": node.position_y},
                "config": node.config or {},
            }
            for node in nodes_result.data
        ],
        "relations": [
            {
                "source": edge.source_key,
                "source_port": edge.source_port,
                "target": edge.target_key,
                "target_port": edge.target_port,
            }
            for edge in edges_result.data
        ],
    }
    return WFResult(WFStatus.SUCCESS, "ok", document)


class _ImportError(Exception):
    pass


def import_workflow(user, workflow_id: int, document: dict | None = None) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error
    document = document or {}
    if not isinstance(document, dict):
        return WFResult(WFStatus.PARAM_ERR, "导入内容必须是 JSON 对象")
    if document.get("format") not in (None, "", "huishutai.workflow"):
        return WFResult(WFStatus.PARAM_ERR, "不支持的工作流文件格式")

    nodes_doc = document.get("nodes")
    relations_doc = document.get("relations", [])
    if relations_doc is None:
        relations_doc = []
    if not isinstance(nodes_doc, list) or not isinstance(relations_doc, list):
        return WFResult(WFStatus.PARAM_ERR, "nodes / relations 必须是数组")
    if len(nodes_doc) > 200:
        return WFResult(WFStatus.PARAM_ERR, "单次导入节点不能超过 200 个")
    if len(relations_doc) > 500:
        return WFResult(WFStatus.PARAM_ERR, "单次导入连线不能超过 500 条")

    try:
        available_types = set(list_node_files())
        prepared_nodes: list[dict] = []
        used_keys: set[str] = set()
        for index, item in enumerate(nodes_doc):
            if not isinstance(item, dict):
                raise _ImportError(f"第 {index + 1} 个节点格式不正确")
            node_type = str(item.get("type") or item.get("node_type") or "").strip()
            if node_type not in available_types:
                raise _ImportError(f"第 {index + 1} 个节点类型不存在：{node_type}")
            key = str(item.get("key") or "").strip() or uuid.uuid4().hex
            if not key or key in used_keys:
                raise _ImportError(f"节点 key 重复或为空：{key}")
            used_keys.add(key)
            position = item.get("position", {})
            if position is None:
                position = {}
            if not isinstance(position, dict):
                raise _ImportError(f"节点 {key} 的 position 格式不正确")
            try:
                x = float(position.get("x") or 0)
                y = float(position.get("y") or 0)
            except (TypeError, ValueError) as exc:
                raise _ImportError(f"节点 {key} 的坐标不是数字") from exc
            config = item.get("config", {})
            if config is None:
                config = {}
            if not isinstance(config, dict):
                raise _ImportError(f"节点 {key} 的 config 必须是对象")
            try:
                meta = get_node_meta(node_type)
            except NodeError as exc:
                raise _ImportError(str(exc)) from exc
            name = str(item.get("name") or meta.get("name") or node_type).strip()[:100]
            prepared_nodes.append(
                {
                    "key": key,
                    "node_type": node_type,
                    "name": name,
                    "position_x": x,
                    "position_y": y,
                    "config": config,
                }
            )

        prepared_edges: list[dict] = []
        edge_seen: set[tuple] = set()
        for index, item in enumerate(relations_doc):
            if not isinstance(item, dict):
                raise _ImportError(f"第 {index + 1} 条连线格式不正确")
            source_key = str(item.get("source") or "").strip()
            target_key = str(item.get("target") or "").strip()
            source_port = str(item.get("source_port") or "out").strip()[:64]
            target_port = str(item.get("target_port") or "in").strip()[:64]
            if source_key not in used_keys or target_key not in used_keys:
                raise _ImportError(f"第 {index + 1} 条连线引用了不存在的节点")
            if source_key == target_key:
                raise _ImportError(f"第 {index + 1} 条连线不能连接自身")
            signature = (source_key, source_port, target_key, target_port)
            if signature in edge_seen:
                raise _ImportError("存在重复连线")
            edge_seen.add(signature)
            prepared_edges.append(
                {
                    "source_key": source_key,
                    "source_port": source_port,
                    "target_key": target_key,
                    "target_port": target_port,
                }
            )

        workflow_fields: dict = {}
        if isinstance(document.get("name"), str) and document["name"].strip():
            workflow_fields["name"] = document["name"].strip()[:100]
        if isinstance(document.get("description"), str):
            workflow_fields["description"] = document["description"].strip()[:500]

        _validate_import_graph(prepared_nodes, prepared_edges)
        with transaction.atomic():
            workflow_edge_crud.delete_by_workflow(workflow.pk)
            workflow_node_crud.delete_by_workflow(workflow.pk)
            for item in prepared_nodes:
                result = workflow_node_crud.create(workflow=workflow, version=1, **item)
                if result.code != DBStatus.SUCCESS:
                    raise _ImportError(result.message)
            for item in prepared_edges:
                result = workflow_edge_crud.create(workflow=workflow, **item)
                if result.code != DBStatus.SUCCESS:
                    raise _ImportError(result.message)
            if workflow_fields:
                workflow_crud.update(workflow.pk, **workflow_fields)
    except _ImportError as exc:
        return WFResult(WFStatus.PARAM_ERR, f"导入失败：{exc}")

    latest = workflow_crud.get_by_pk(workflow.pk)
    workflow = latest.data if latest.code == DBStatus.SUCCESS else workflow
    _record_event(
        workflow,
        user,
        "imported",
        {"nodes": len(prepared_nodes), "relations": len(prepared_edges)},
    )
    return _state(workflow, _role_for(workflow, user) or "owner")


# ==================== 执行 ====================
def run_workflow(user, workflow_id: int) -> WFResult:
    workflow, _role, error = _access(user, workflow_id, edit=True)
    if error:
        return error

    nodes_result = workflow_node_crud.list_by_workflow(workflow.pk)
    edges_result = workflow_edge_crud.list_by_workflow(workflow.pk)
    if nodes_result.code != DBStatus.SUCCESS:
        return _from_db(nodes_result)
    if edges_result.code != DBStatus.SUCCESS:
        return _from_db(edges_result)

    result = executor.run_graph(user, workflow, nodes_result.data, edges_result.data)
    _record_event(
        workflow,
        user,
        "run",
        {
            "status": result.get("status"),
            "steps": len(result.get("steps") or []),
            "duration_ms": result.get("duration_ms"),
        },
    )
    return WFResult(
        WFStatus.SUCCESS,
        "执行完成" if result.get("status") == "success" else "执行失败",
        result,
    )
