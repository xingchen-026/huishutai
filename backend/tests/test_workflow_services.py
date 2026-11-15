"""Workflow 业务层测试：工作流、成员、节点、连线、事件、导入导出与执行。

覆盖 backend/Workflow/services.py 的行为契约。测试使用内存 SQLite 与测试专用
settings，不依赖 PostgreSQL / MinIO / 外部网络（执行用例只用 start / condition 节点）。

运行（在 backend/ 目录，PowerShell）：
    $env:DJANGO_SETTINGS_MODULE = "tests.settings"
    .venv/Scripts/python.exe -B manage.py test tests.test_workflow_services -v 2
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from sqldb.models import (
    User,
    Workflow,
    WorkflowEdge,
    WorkflowEvent,
    WorkflowMember,
    WorkflowNode,
)
from Workflow import services
from Workflow.result import WFStatus

NODE_TYPES = ["condition", "http", "llm", "start"]


def make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, password="x")


class WorkflowServiceTestCase(TestCase):
    """公共构造：用户、工作流、成员、节点、连线。"""

    def setUp(self):
        self.owner = make_user("owner")
        self.editor = make_user("editor")
        self.viewer = make_user("viewer")
        self.outsider = make_user("outsider")

    # ---------- 构造辅助 ----------
    def create_workflow(self, user=None, name="测试工作流", description="描述"):
        result = services.create_workflow(
            user or self.owner, {"name": name, "description": description}
        )
        self.assertTrue(result.success, result.message)
        return result.data["workflow"]["id"]

    def shared_workflow(self):
        """owner 创建并邀请 editor / viewer 的工作流。"""
        workflow_id = self.create_workflow()
        self.add_member(workflow_id, "editor", "editor")
        self.add_member(workflow_id, "viewer", "viewer")
        return workflow_id

    def add_member(self, workflow_id, username, role="editor"):
        result = services.add_member(self.owner, workflow_id, {"username": username, "role": role})
        self.assertTrue(result.success, result.message)
        return result

    def add_node(self, workflow_id, node_type="start", **extra):
        payload = {"node_type": node_type, "position": {"x": 10, "y": 20}}
        payload.update(extra)
        result = services.add_node(self.owner, workflow_id, payload)
        self.assertTrue(result.success, result.message)
        return result.data["node"]

    def add_relation(
        self, workflow_id, source_key, target_key, source_port="out", target_port="in"
    ):
        result = services.add_relation(
            self.owner,
            workflow_id,
            {
                "source_key": source_key,
                "source_port": source_port,
                "target_key": target_key,
                "target_port": target_port,
            },
        )
        self.assertTrue(result.success, result.message)
        return result.data["relation"]

    def workflow_node_keys(self, workflow_id):
        return list(
            WorkflowNode.objects.filter(workflow_id=workflow_id)
            .order_by("created_at")
            .values_list("key", flat=True)
        )

    def events(self, workflow_id, after=0, limit=100):
        result = services.list_events(self.owner, workflow_id, after, limit)
        self.assertTrue(result.success, result.message)
        return result.data

    def standard_graph(self, workflow_id, payload='{"ok": 1}'):
        """start --out--> condition 的最小可执行图。"""
        start = self.add_node(workflow_id, "start", config={"payload": payload})
        condition = self.add_node(
            workflow_id,
            "condition",
            config={"field": "payload.ok", "operator": "eq", "value": "1"},
        )
        self.add_relation(workflow_id, start["key"], condition["key"])
        return start, condition


# ==================== 工作流 CRUD ====================
class WorkflowCrudServiceTest(WorkflowServiceTestCase):
    def test_create_workflow_trims_and_truncates_fields(self):
        result = services.create_workflow(
            self.owner, {"name": "  " + "长" * 150 + "  ", "description": "描" * 600}
        )
        self.assertTrue(result.success, result.message)
        workflow = result.data["workflow"]
        self.assertEqual(workflow["name"], ("长" * 150)[:100])
        self.assertEqual(len(workflow["name"]), 100)
        self.assertEqual(len(workflow["description"]), 500)
        self.assertEqual(workflow["role"], "owner")
        self.assertEqual(workflow["node_count"], 0)
        self.assertEqual(workflow["owner_id"], self.owner.pk)
        self.assertEqual(workflow["owner_name"], "owner")
        self.assertEqual(Workflow.objects.count(), 1)

    def test_create_workflow_requires_non_blank_name(self):
        cases = (None, {}, {"name": None}, {"name": ""}, {"name": "   "})
        for data in cases:
            with self.subTest(data=data):
                result = services.create_workflow(self.owner, data)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
                self.assertIn("名称不能为空", result.message)
        self.assertEqual(Workflow.objects.count(), 0)

    def test_create_workflow_records_created_event(self):
        workflow_id = self.create_workflow(name="事件工作流")
        data = self.events(workflow_id)
        self.assertEqual(data["last_event_seq"], 1)
        self.assertEqual(len(data["events"]), 1)
        event = data["events"][0]
        self.assertEqual(event["op"], "workflow_created")
        self.assertEqual(event["payload"], {"name": "事件工作流"})
        self.assertEqual(event["actor_id"], self.owner.pk)
        self.assertEqual(event["actor_name"], "owner")
        self.assertTrue(event["created_at"])

    def test_get_workflow_returns_full_state(self):
        workflow_id = self.create_workflow(name="状态工作流")
        node = self.add_node(workflow_id, "condition")
        result = services.get_workflow(self.owner, workflow_id)
        self.assertTrue(result.success, result.message)
        data = result.data
        self.assertEqual(
            set(data),
            {"workflow", "nodes", "relations", "members", "last_event_seq", "node_types"},
        )
        self.assertEqual(data["workflow"]["role"], "owner")
        self.assertEqual(data["workflow"]["node_count"], 1)
        self.assertEqual([item["key"] for item in data["nodes"]], [node["key"]])
        self.assertEqual(data["relations"], [])
        self.assertEqual([member["role"] for member in data["members"]], ["owner"])
        self.assertEqual(data["node_types"], NODE_TYPES)
        self.assertEqual(data["last_event_seq"], 2)

    def test_get_workflow_not_found_and_forbidden(self):
        missing = services.get_workflow(self.owner, 999999)
        self.assertEqual(missing.code, WFStatus.NOT_FOUND)
        self.assertEqual(missing.message, "工作流不存在")

        workflow_id = self.shared_workflow()
        forbidden = services.get_workflow(self.outsider, workflow_id)
        self.assertEqual(forbidden.code, WFStatus.FORBIDDEN)
        allowed = services.get_workflow(self.viewer, workflow_id)
        self.assertTrue(allowed.success, allowed.message)
        self.assertEqual(allowed.data["workflow"]["role"], "viewer")

    def test_list_workflows_only_returns_own_and_invited(self):
        own = self.create_workflow(name="自己的")
        shared = self.shared_workflow()
        editor_own = self.create_workflow(user=self.editor, name="编辑自己的")

        owner_list = services.list_workflows(self.owner)
        self.assertTrue(owner_list.success, owner_list.message)
        self.assertEqual(owner_list.data["total"], 2)
        self.assertEqual({item["id"] for item in owner_list.data["workflows"]}, {own, shared})

        editor_list = services.list_workflows(self.editor)
        self.assertEqual(editor_list.data["total"], 2)
        roles = {item["id"]: item["role"] for item in editor_list.data["workflows"]}
        self.assertEqual(roles[shared], "editor")
        self.assertEqual(roles[editor_own], "owner")

        self.assertEqual(services.list_workflows(self.outsider).data["total"], 0)

    def test_list_workflows_counts_nodes(self):
        workflow_id = self.create_workflow()
        self.add_node(workflow_id, "start")
        self.add_node(workflow_id, "condition")
        result = services.list_workflows(self.owner)
        self.assertEqual(result.data["workflows"][0]["node_count"], 2)

    def test_list_workflows_orders_by_updated_at_desc(self):
        first = self.create_workflow(name="先创建")
        second = self.create_workflow(name="后创建")
        now = timezone.now()
        Workflow.objects.filter(pk=first).update(updated_at=now - timedelta(minutes=10))
        Workflow.objects.filter(pk=second).update(updated_at=now - timedelta(minutes=5))
        data = services.list_workflows(self.owner).data
        self.assertEqual([item["id"] for item in data["workflows"]], [second, first])

        Workflow.objects.filter(pk=first).update(updated_at=now)
        data = services.list_workflows(self.owner).data
        self.assertEqual([item["id"] for item in data["workflows"]], [first, second])

    def test_update_workflow_success_and_event(self):
        workflow_id = self.create_workflow(name="旧名称", description="旧描述")
        result = services.update_workflow(
            self.owner, workflow_id, {"name": "新名称", "description": "新描述"}
        )
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["workflow"]["name"], "新名称")
        self.assertEqual(result.data["workflow"]["role"], "owner")
        stored = Workflow.objects.get(pk=workflow_id)
        self.assertEqual(stored.name, "新名称")
        self.assertEqual(stored.description, "新描述")
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "workflow_updated")
        self.assertEqual(event["payload"], {"name": "新名称", "description": "新描述"})

        editor_result = services.update_workflow(
            self.editor, self.shared_workflow(), {"name": "编辑改名"}
        )
        self.assertTrue(editor_result.success, editor_result.message)
        self.assertEqual(editor_result.data["workflow"]["role"], "editor")

    def test_update_workflow_validation_errors(self):
        workflow_id = self.create_workflow()
        cases = ({}, None, {"name": ""}, {"name": "   "})
        for data in cases:
            with self.subTest(data=data):
                result = services.update_workflow(self.owner, workflow_id, data)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(Workflow.objects.get(pk=workflow_id).name, "测试工作流")

    def test_update_workflow_permission_errors(self):
        workflow_id = self.shared_workflow()
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                result = services.update_workflow(user, workflow_id, {"name": "越权"})
                self.assertEqual(result.code, WFStatus.FORBIDDEN)
        self.assertEqual(
            services.update_workflow(self.owner, 999999, {"name": "x"}).code,
            WFStatus.NOT_FOUND,
        )

    def test_delete_workflow_cascades(self):
        workflow_id = self.create_workflow()
        self.add_member(workflow_id, "editor")
        start = self.add_node(workflow_id, "start")
        condition = self.add_node(workflow_id, "condition")
        self.add_relation(workflow_id, start["key"], condition["key"])
        self.assertTrue(WorkflowEvent.objects.filter(workflow_id=workflow_id).exists())

        result = services.delete_workflow(self.owner, workflow_id)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["id"], workflow_id)
        self.assertFalse(Workflow.objects.filter(pk=workflow_id).exists())
        self.assertFalse(WorkflowNode.objects.filter(workflow_id=workflow_id).exists())
        self.assertFalse(WorkflowEdge.objects.filter(workflow_id=workflow_id).exists())
        self.assertFalse(WorkflowMember.objects.filter(workflow_id=workflow_id).exists())
        self.assertFalse(WorkflowEvent.objects.filter(workflow_id=workflow_id).exists())

    def test_delete_workflow_permission_errors(self):
        workflow_id = self.shared_workflow()
        for user in (self.editor, self.viewer, self.outsider):
            with self.subTest(user=user.username):
                result = services.delete_workflow(user, workflow_id)
                self.assertEqual(result.code, WFStatus.FORBIDDEN)
        self.assertTrue(Workflow.objects.filter(pk=workflow_id).exists())
        self.assertEqual(services.delete_workflow(self.owner, 999999).code, WFStatus.NOT_FOUND)


# ==================== 成员 ====================
class MemberServiceTest(WorkflowServiceTestCase):
    def test_add_member_success_and_members_order(self):
        workflow_id = self.create_workflow()
        self.add_member(workflow_id, "editor", "editor")
        self.add_member(workflow_id, "viewer", "viewer")
        data = services.get_workflow(self.owner, workflow_id).data
        self.assertEqual(
            [(item["username"], item["role"]) for item in data["members"]],
            [("owner", "owner"), ("editor", "editor"), ("viewer", "viewer")],
        )
        self.assertTrue(data["members"][0]["created_at"])
        self.assertEqual(WorkflowMember.objects.filter(workflow_id=workflow_id).count(), 2)

    def test_add_member_requires_owner(self):
        workflow_id = self.shared_workflow()
        for user in (self.editor, self.viewer):
            with self.subTest(user=user.username):
                result = services.add_member(
                    user, workflow_id, {"username": "outsider", "role": "editor"}
                )
                self.assertEqual(result.code, WFStatus.FORBIDDEN)
        self.assertEqual(WorkflowMember.objects.filter(workflow_id=workflow_id).count(), 2)

    def test_add_member_validation_errors(self):
        workflow_id = self.create_workflow()
        not_found = services.add_member(
            self.owner, workflow_id, {"username": "ghost", "role": "editor"}
        )
        self.assertEqual(not_found.code, WFStatus.NOT_FOUND)
        self.assertIn("用户不存在", not_found.message)

        add_owner = services.add_member(
            self.owner, workflow_id, {"username": "owner", "role": "editor"}
        )
        self.assertEqual(add_owner.code, WFStatus.PARAM_ERR)
        self.assertIn("创建者", add_owner.message)

        bad_role = services.add_member(
            self.owner, workflow_id, {"username": "editor", "role": "admin"}
        )
        self.assertEqual(bad_role.code, WFStatus.PARAM_ERR)
        self.assertIn("editor 或 viewer", bad_role.message)
        self.assertEqual(WorkflowMember.objects.filter(workflow_id=workflow_id).count(), 0)

    def test_add_member_default_role_is_editor(self):
        workflow_id = self.create_workflow()
        result = services.add_member(self.owner, workflow_id, {"username": "editor"})
        self.assertTrue(result.success, result.message)
        self.assertEqual(WorkflowMember.objects.get(workflow_id=workflow_id).role, "editor")

    def test_add_member_duplicate_rejected(self):
        workflow_id = self.create_workflow()
        self.add_member(workflow_id, "editor", "editor")
        duplicate = services.add_member(
            self.owner, workflow_id, {"username": "editor", "role": "viewer"}
        )
        self.assertEqual(duplicate.code, WFStatus.PARAM_ERR)
        self.assertIn("已是协作者", duplicate.message)
        self.assertEqual(WorkflowMember.objects.filter(workflow_id=workflow_id).count(), 1)

    def test_add_member_records_event(self):
        workflow_id = self.create_workflow()
        self.add_member(workflow_id, "editor", "editor")
        data = self.events(workflow_id)
        self.assertEqual(data["last_event_seq"], 2)
        event = data["events"][-1]
        self.assertEqual(event["op"], "members_changed")
        self.assertEqual(event["payload"], {"added": "editor", "role": "editor"})

    def test_remove_member_success_and_event(self):
        workflow_id = self.create_workflow()
        self.add_member(workflow_id, "editor", "editor")
        result = services.remove_member(self.owner, workflow_id, self.editor.pk)
        self.assertTrue(result.success, result.message)
        self.assertEqual([item["role"] for item in result.data["members"]], ["owner"])
        self.assertEqual(WorkflowMember.objects.filter(workflow_id=workflow_id).count(), 0)
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "members_changed")
        self.assertEqual(event["payload"], {"removed_user_id": self.editor.pk})

    def test_remove_member_errors(self):
        workflow_id = self.shared_workflow()
        missing = services.remove_member(self.owner, workflow_id, 999999)
        self.assertEqual(missing.code, WFStatus.NOT_FOUND)
        self.assertIn("成员不存在", missing.message)

        owner_as_member = services.remove_member(self.owner, workflow_id, self.owner.pk)
        self.assertEqual(owner_as_member.code, WFStatus.NOT_FOUND)

        editor_remove = services.remove_member(self.editor, workflow_id, self.viewer.pk)
        self.assertEqual(editor_remove.code, WFStatus.FORBIDDEN)
        viewer_remove = services.remove_member(self.viewer, workflow_id, self.editor.pk)
        self.assertEqual(viewer_remove.code, WFStatus.FORBIDDEN)
        self.assertEqual(WorkflowMember.objects.filter(workflow_id=workflow_id).count(), 2)


# ==================== 节点 ====================
class NodeServiceTest(WorkflowServiceTestCase):
    def test_add_node_defaults_and_event(self):
        workflow_id = self.create_workflow()
        result = services.add_node(
            self.owner,
            workflow_id,
            {"node_type": "start", "position": {"x": 12.5, "y": -3}},
        )
        self.assertTrue(result.success, result.message)
        node = result.data["node"]
        self.assertRegex(node["key"], r"^[0-9a-f]{32}$")
        self.assertEqual(node["node_type"], "start")
        self.assertEqual(node["name"], "开始")
        self.assertEqual(node["position"], {"x": 12.5, "y": -3.0})
        self.assertEqual(node["config"], {})
        self.assertEqual(node["version"], 1)
        stored = WorkflowNode.objects.get(workflow_id=workflow_id, key=node["key"])
        self.assertEqual(stored.version, 1)
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "node_added")
        self.assertEqual(event["payload"]["node"]["key"], node["key"])

    def test_add_node_default_and_custom_names(self):
        workflow_id = self.create_workflow()
        self.assertEqual(self.add_node(workflow_id, "condition")["name"], "条件分支")
        self.assertEqual(
            self.add_node(workflow_id, "start", name="自定义节点")["name"], "自定义节点"
        )
        long_name = self.add_node(workflow_id, "start", name="名" * 120)["name"]
        self.assertEqual(len(long_name), 100)

    def test_add_node_unknown_type(self):
        workflow_id = self.create_workflow()
        for node_type in ("bogus", "", "Bad Type"):
            with self.subTest(node_type=node_type):
                result = services.add_node(self.owner, workflow_id, {"node_type": node_type})
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(WorkflowNode.objects.filter(workflow_id=workflow_id).count(), 0)

    def test_add_node_invalid_position(self):
        workflow_id = self.create_workflow()
        cases = ("abc", {"x": "a"}, {"y": [1]}, 123)
        for position in cases:
            with self.subTest(position=position):
                result = services.add_node(
                    self.owner,
                    workflow_id,
                    {"node_type": "start", "position": position},
                )
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(WorkflowNode.objects.filter(workflow_id=workflow_id).count(), 0)

    def test_add_node_should_reject_non_object_empty_list_position(self):
        """已知缺陷：position=[] 被 falsy 默认值静默当成空对象，应返回 PARAM_ERR。"""
        workflow_id = self.create_workflow()
        result = services.add_node(self.owner, workflow_id, {"node_type": "start", "position": []})
        self.assertEqual(result.code, WFStatus.PARAM_ERR)

    def test_add_node_invalid_config(self):
        workflow_id = self.create_workflow()
        for config in ([1], "x", 5):
            with self.subTest(config=config):
                result = services.add_node(
                    self.owner,
                    workflow_id,
                    {"node_type": "start", "position": {"x": 0, "y": 0}, "config": config},
                )
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(WorkflowNode.objects.filter(workflow_id=workflow_id).count(), 0)

    def test_add_node_permission(self):
        workflow_id = self.shared_workflow()
        payload = {"node_type": "start", "position": {"x": 1, "y": 2}}
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                self.assertEqual(
                    services.add_node(user, workflow_id, payload).code, WFStatus.FORBIDDEN
                )
        self.assertTrue(services.add_node(self.editor, workflow_id, payload).success)

    def test_update_node_success_bumps_version(self):
        workflow_id = self.create_workflow()
        node = self.add_node(workflow_id, "start")
        result = services.update_node(
            self.owner,
            workflow_id,
            node["key"],
            {
                "base_version": 1,
                "name": "新名字",
                "position": {"x": 5, "y": 6},
                "config": {"payload": "{}"},
            },
        )
        self.assertTrue(result.success, result.message)
        updated = result.data["node"]
        self.assertEqual(updated["name"], "新名字")
        self.assertEqual(updated["position"], {"x": 5.0, "y": 6.0})
        self.assertEqual(updated["config"], {"payload": "{}"})
        self.assertEqual(updated["version"], 2)
        self.assertEqual(
            WorkflowNode.objects.get(workflow_id=workflow_id, key=node["key"]).version, 2
        )
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "node_updated")
        self.assertEqual(event["payload"]["node"]["version"], 2)

    def test_update_node_requires_base_version(self):
        workflow_id = self.create_workflow()
        node = self.add_node(workflow_id, "start")
        cases = (
            {},
            {"name": "x"},
            {"base_version": None},
            {"base_version": "abc"},
            {"base_version": [1]},
        )
        for data in cases:
            with self.subTest(data=data):
                result = services.update_node(self.owner, workflow_id, node["key"], data)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(
            WorkflowNode.objects.get(workflow_id=workflow_id, key=node["key"]).version, 1
        )

    def test_update_node_should_reject_non_integer_base_version(self):
        """已知缺陷：base_version=1.5 被 int() 静默截断为 1 并通过乐观锁，应返回 PARAM_ERR。"""
        workflow_id = self.create_workflow()
        node = self.add_node(workflow_id, "start")
        result = services.update_node(
            self.owner, workflow_id, node["key"], {"base_version": 1.5, "name": "x"}
        )
        self.assertEqual(result.code, WFStatus.PARAM_ERR)

    def test_update_node_validation_errors(self):
        workflow_id = self.create_workflow()
        node = self.add_node(workflow_id, "start")
        cases = ({"name": ""}, {"name": "   "}, {"position": "bad"}, {"config": [1]}, {})
        for fields in cases:
            with self.subTest(fields=fields):
                data = {"base_version": 1, **fields}
                result = services.update_node(self.owner, workflow_id, node["key"], data)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(
            WorkflowNode.objects.get(workflow_id=workflow_id, key=node["key"]).version, 1
        )

    def test_update_node_version_conflict(self):
        workflow_id = self.create_workflow()
        node = self.add_node(workflow_id, "start")
        first = services.update_node(
            self.owner, workflow_id, node["key"], {"base_version": 1, "name": "v2"}
        )
        self.assertTrue(first.success, first.message)
        second = services.update_node(
            self.owner, workflow_id, node["key"], {"base_version": 1, "name": "冲突写入"}
        )
        self.assertEqual(second.code, WFStatus.CONFLICT)
        self.assertIn("请刷新", second.message)
        stored = WorkflowNode.objects.get(workflow_id=workflow_id, key=node["key"])
        self.assertEqual(stored.name, "v2")
        self.assertEqual(stored.version, 2)

    def test_update_node_not_found_and_forbidden(self):
        workflow_id = self.shared_workflow()
        missing = services.update_node(
            self.owner, workflow_id, "missing-key", {"base_version": 1, "name": "x"}
        )
        self.assertEqual(missing.code, WFStatus.NOT_FOUND)
        node = self.add_node(workflow_id, "start")
        forbidden = services.update_node(
            self.viewer, workflow_id, node["key"], {"base_version": 1, "name": "x"}
        )
        self.assertEqual(forbidden.code, WFStatus.FORBIDDEN)

    def test_delete_node_cleans_relations_and_event(self):
        workflow_id = self.create_workflow()
        start = self.add_node(workflow_id, "start")
        condition = self.add_node(workflow_id, "condition")
        self.add_relation(workflow_id, start["key"], condition["key"])
        result = services.delete_node(self.owner, workflow_id, start["key"])
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["key"], start["key"])
        self.assertFalse(WorkflowNode.objects.filter(key=start["key"]).exists())
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=workflow_id).count(), 0)
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "node_deleted")
        self.assertEqual(event["payload"], {"key": start["key"]})

    def test_delete_node_not_found_and_forbidden(self):
        workflow_id = self.shared_workflow()
        missing = services.delete_node(self.owner, workflow_id, "missing-key")
        self.assertEqual(missing.code, WFStatus.NOT_FOUND)
        node = self.add_node(workflow_id, "start")
        forbidden = services.delete_node(self.viewer, workflow_id, node["key"])
        self.assertEqual(forbidden.code, WFStatus.FORBIDDEN)
        self.assertTrue(WorkflowNode.objects.filter(key=node["key"]).exists())


# ==================== 连线 ====================
class RelationServiceTest(WorkflowServiceTestCase):
    def setUp(self):
        super().setUp()
        self.workflow_id = self.create_workflow()
        self.start_node = self.add_node(self.workflow_id, "start")
        self.condition_node = self.add_node(self.workflow_id, "condition")
        self.http_node = self.add_node(self.workflow_id, "http")
        self.second_workflow_id = self.create_workflow(name="第二个工作流")
        self.second_start = self.add_node(self.second_workflow_id, "start")
        self.second_condition = self.add_node(self.second_workflow_id, "condition")

    def test_add_relation_success_and_event(self):
        result = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.start_node["key"], "target_key": self.condition_node["key"]},
        )
        self.assertTrue(result.success, result.message)
        relation = result.data["relation"]
        self.assertIsInstance(relation["id"], int)
        self.assertEqual(relation["source_key"], self.start_node["key"])
        self.assertEqual(relation["source_port"], "out")
        self.assertEqual(relation["target_key"], self.condition_node["key"])
        self.assertEqual(relation["target_port"], "in")
        self.assertTrue(relation["created_at"])
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 1)
        event = self.events(self.workflow_id)["events"][-1]
        self.assertEqual(event["op"], "edge_added")
        self.assertEqual(event["payload"]["relation"]["id"], relation["id"])

    def test_add_relation_accepts_condition_true_false_ports(self):
        self.add_relation(
            self.workflow_id,
            self.condition_node["key"],
            self.http_node["key"],
            source_port="true",
        )
        self.add_relation(
            self.workflow_id,
            self.condition_node["key"],
            self.http_node["key"],
            source_port="false",
        )
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 2)

    def test_add_relation_missing_keys_self_loop_and_missing_node(self):
        cases = (
            {"target_key": self.condition_node["key"]},
            {"source_key": self.start_node["key"]},
            {"source_key": self.start_node["key"], "target_key": self.start_node["key"]},
        )
        for data in cases:
            with self.subTest(data=data):
                result = services.add_relation(self.owner, self.workflow_id, data)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)

        missing = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.start_node["key"], "target_key": "not-exists"},
        )
        self.assertEqual(missing.code, WFStatus.NOT_FOUND)

        cross_workflow = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.start_node["key"], "target_key": self.second_start["key"]},
        )
        self.assertEqual(cross_workflow.code, WFStatus.NOT_FOUND)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 0)

    def test_add_relation_invalid_ports(self):
        bad_source = services.add_relation(
            self.owner,
            self.workflow_id,
            {
                "source_key": self.condition_node["key"],
                "source_port": "maybe",
                "target_key": self.http_node["key"],
            },
        )
        self.assertEqual(bad_source.code, WFStatus.PARAM_ERR)
        self.assertIn("源端口", bad_source.message)

        bad_target = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.http_node["key"], "target_key": self.start_node["key"]},
        )
        self.assertEqual(bad_target.code, WFStatus.PARAM_ERR)
        self.assertIn("目标端口", bad_target.message)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 0)

    def test_add_relation_duplicate_rejected(self):
        self.add_relation(self.workflow_id, self.start_node["key"], self.condition_node["key"])
        duplicate = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.start_node["key"], "target_key": self.condition_node["key"]},
        )
        self.assertEqual(duplicate.code, WFStatus.PARAM_ERR)
        self.assertIn("已存在", duplicate.message)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 1)

    def test_add_relation_rejects_direct_cycle(self):
        self.add_relation(
            self.workflow_id,
            self.condition_node["key"],
            self.http_node["key"],
            source_port="true",
        )
        cycle = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.http_node["key"], "target_key": self.condition_node["key"]},
        )
        self.assertEqual(cycle.code, WFStatus.PARAM_ERR)
        self.assertIn("环", cycle.message)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 1)

    def test_add_relation_rejects_indirect_cycle(self):
        second_condition = self.add_node(self.workflow_id, "condition")
        self.add_relation(self.workflow_id, self.start_node["key"], self.condition_node["key"])
        self.add_relation(
            self.workflow_id,
            self.condition_node["key"],
            second_condition["key"],
            source_port="true",
        )
        self.add_relation(
            self.workflow_id,
            second_condition["key"],
            self.http_node["key"],
            source_port="true",
        )
        cycle = services.add_relation(
            self.owner,
            self.workflow_id,
            {"source_key": self.http_node["key"], "target_key": self.condition_node["key"]},
        )
        self.assertEqual(cycle.code, WFStatus.PARAM_ERR)
        self.assertIn("环", cycle.message)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 3)

    def test_add_relation_permission(self):
        workflow_id = self.shared_workflow()
        start = self.add_node(workflow_id, "start")
        condition = self.add_node(workflow_id, "condition")
        payload = {"source_key": start["key"], "target_key": condition["key"]}
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                result = services.add_relation(user, workflow_id, payload)
                self.assertEqual(result.code, WFStatus.FORBIDDEN)
        self.assertTrue(services.add_relation(self.editor, workflow_id, payload).success)

    def test_delete_relation_success_and_event(self):
        relation = self.add_relation(
            self.workflow_id, self.start_node["key"], self.condition_node["key"]
        )
        result = services.delete_relation(self.owner, self.workflow_id, relation["id"])
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["id"], relation["id"])
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 0)
        event = self.events(self.workflow_id)["events"][-1]
        self.assertEqual(event["op"], "edge_deleted")
        self.assertEqual(event["payload"], {"id": relation["id"]})

    def test_delete_relation_not_found_and_cross_workflow(self):
        not_found = services.delete_relation(self.owner, self.workflow_id, 999999)
        self.assertEqual(not_found.code, WFStatus.NOT_FOUND)

        relation = self.add_relation(
            self.second_workflow_id,
            self.second_start["key"],
            self.second_condition["key"],
        )
        cross = services.delete_relation(self.owner, self.workflow_id, relation["id"])
        self.assertEqual(cross.code, WFStatus.NOT_FOUND)
        self.assertTrue(WorkflowEdge.objects.filter(pk=relation["id"]).exists())

    def test_delete_relation_permission(self):
        relation = self.add_relation(
            self.workflow_id, self.start_node["key"], self.condition_node["key"]
        )
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                result = services.delete_relation(user, self.workflow_id, relation["id"])
                self.assertEqual(result.code, WFStatus.FORBIDDEN)
        self.assertTrue(WorkflowEdge.objects.filter(pk=relation["id"]).exists())


# ==================== 事件 ====================
class EventServiceTest(WorkflowServiceTestCase):
    def test_write_operations_record_events_in_order(self):
        workflow_id = self.create_workflow()
        data = self.events(workflow_id)
        self.assertEqual(data["last_event_seq"], 1)
        self.assertEqual(data["events"][0]["op"], "workflow_created")

        self.assertTrue(services.update_workflow(self.owner, workflow_id, {"name": "改名"}).success)
        self.add_member(workflow_id, "editor", "editor")
        start = self.add_node(workflow_id, "start")
        condition = self.add_node(workflow_id, "condition")
        self.assertTrue(
            services.update_node(
                self.owner, workflow_id, condition["key"], {"base_version": 1, "name": "条件"}
            ).success
        )
        relation = self.add_relation(workflow_id, start["key"], condition["key"])
        self.assertTrue(services.run_workflow(self.owner, workflow_id).success)

        document = {
            "format": "huishutai.workflow",
            "nodes": [
                {"key": "n1", "type": "start", "position": {"x": 0, "y": 0}},
                {"key": "n2", "type": "condition", "position": {"x": 1, "y": 1}},
            ],
            "relations": [{"source": "n1", "target": "n2"}],
        }
        imported = services.import_workflow(self.owner, workflow_id, document)
        self.assertTrue(imported.success, imported.message)
        imported_relation = imported.data["relations"][0]
        self.assertTrue(
            services.delete_relation(self.owner, workflow_id, imported_relation["id"]).success
        )
        self.assertTrue(services.delete_node(self.owner, workflow_id, "n1").success)
        self.assertTrue(services.remove_member(self.owner, workflow_id, self.editor.pk).success)

        data = self.events(workflow_id)
        self.assertEqual(data["last_event_seq"], 12)
        self.assertEqual(
            [event["op"] for event in data["events"]],
            [
                "workflow_created",
                "workflow_updated",
                "members_changed",
                "node_added",
                "node_added",
                "node_updated",
                "edge_added",
                "run",
                "imported",
                "edge_deleted",
                "node_deleted",
                "members_changed",
            ],
        )
        ids = [event["id"] for event in data["events"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), 12)
        self.assertTrue(all(event["actor_name"] == "owner" for event in data["events"]))
        self.assertTrue(all(event["created_at"] for event in data["events"]))
        self.assertFalse(WorkflowEdge.objects.filter(pk=relation["id"]).exists())

    def test_list_events_after_filter(self):
        workflow_id = self.create_workflow()
        self.add_node(workflow_id, "start")
        self.add_node(workflow_id, "condition")
        data = self.events(workflow_id)
        self.assertEqual(len(data["events"]), 3)
        first_id = data["events"][0]["id"]

        filtered = self.events(workflow_id, after=first_id)
        self.assertEqual([event["id"] for event in filtered["events"]], [2, 3])
        self.assertEqual(filtered["last_event_seq"], 3)

        after_last = self.events(workflow_id, after=data["events"][-1]["id"])
        self.assertEqual(after_last["events"], [])
        self.assertEqual(after_last["last_event_seq"], 3)

        all_events = self.events(workflow_id, after=0)
        self.assertEqual(len(all_events["events"]), 3)

    def test_list_events_limit(self):
        workflow_id = self.create_workflow()
        for _ in range(3):
            self.add_node(workflow_id, "start")
        data = self.events(workflow_id, limit=2)
        self.assertEqual(len(data["events"]), 2)
        self.assertEqual([event["id"] for event in data["events"]], [1, 2])
        self.assertEqual(len(self.events(workflow_id, limit=500)["events"]), 4)

    def test_list_events_permissions(self):
        workflow_id = self.shared_workflow()
        self.assertTrue(services.list_events(self.viewer, workflow_id).success)
        self.assertEqual(services.list_events(self.outsider, workflow_id).code, WFStatus.FORBIDDEN)
        self.assertEqual(services.list_events(self.owner, 999999).code, WFStatus.NOT_FOUND)


# ==================== 导入 / 导出 ====================
class ImportExportServiceTest(WorkflowServiceTestCase):
    def setUp(self):
        super().setUp()
        self.workflow_id = self.create_workflow(name="原始名称", description="原始描述")
        self.start_node = self.add_node(self.workflow_id, "start")
        self.condition_node = self.add_node(self.workflow_id, "condition")
        self.relation = self.add_relation(
            self.workflow_id, self.start_node["key"], self.condition_node["key"]
        )
        self.import_document = {
            "format": "huishutai.workflow",
            "format_version": 1,
            "name": "导入后的名称",
            "description": "导入后的描述",
            "nodes": [
                {
                    "key": "imported-start",
                    "type": "start",
                    "name": "导入入口",
                    "position": {"x": 1, "y": 2},
                    "config": {"payload": '{"ok": 1}'},
                },
                {
                    "key": "imported-condition",
                    "type": "condition",
                    "position": {"x": 3, "y": 4},
                    "config": {"field": "payload.ok", "operator": "eq", "value": "1"},
                },
            ],
            "relations": [
                {
                    "source": "imported-start",
                    "source_port": "out",
                    "target": "imported-condition",
                    "target_port": "in",
                }
            ],
        }

    def test_export_document_structure(self):
        result = services.export_workflow(self.owner, self.workflow_id)
        self.assertTrue(result.success, result.message)
        document = result.data
        self.assertEqual(
            set(document),
            {"format", "format_version", "name", "description", "nodes", "relations"},
        )
        self.assertEqual(document["format"], "huishutai.workflow")
        self.assertEqual(document["format_version"], 1)
        self.assertEqual(document["name"], "原始名称")
        self.assertEqual(document["description"], "原始描述")
        self.assertEqual(len(document["nodes"]), 2)
        self.assertEqual(set(document["nodes"][0]), {"key", "type", "name", "position", "config"})
        exported = {node["key"]: node for node in document["nodes"]}
        self.assertEqual(exported[self.start_node["key"]]["type"], "start")
        self.assertEqual(exported[self.start_node["key"]]["position"], {"x": 10.0, "y": 20.0})
        self.assertEqual(
            set(document["relations"][0]),
            {"source", "source_port", "target", "target_port"},
        )
        self.assertEqual(document["relations"][0]["source"], self.start_node["key"])
        self.assertEqual(document["relations"][0]["target"], self.condition_node["key"])

    def test_export_permission(self):
        workflow_id = self.shared_workflow()
        self.assertTrue(services.export_workflow(self.viewer, workflow_id).success)
        self.assertEqual(
            services.export_workflow(self.outsider, workflow_id).code, WFStatus.FORBIDDEN
        )
        self.assertEqual(services.export_workflow(self.owner, 999999).code, WFStatus.NOT_FOUND)

    def test_import_success_replaces_graph_and_metadata(self):
        result = services.import_workflow(self.owner, self.workflow_id, self.import_document)
        self.assertTrue(result.success, result.message)
        state = result.data
        self.assertEqual(state["workflow"]["name"], "导入后的名称")
        self.assertEqual(state["workflow"]["description"], "导入后的描述")
        self.assertEqual(
            [node["key"] for node in state["nodes"]],
            ["imported-start", "imported-condition"],
        )
        self.assertEqual(len(state["relations"]), 1)
        self.assertEqual(state["relations"][0]["source_key"], "imported-start")
        self.assertEqual(state["workflow"]["node_count"], 2)
        self.assertEqual(
            self.workflow_node_keys(self.workflow_id), ["imported-start", "imported-condition"]
        )
        event = self.events(self.workflow_id)["events"][-1]
        self.assertEqual(event["op"], "imported")
        self.assertEqual(event["payload"], {"nodes": 2, "relations": 1})

        run = services.run_workflow(self.owner, self.workflow_id)
        self.assertTrue(run.success, run.message)
        self.assertEqual(run.data["status"], "success")
        self.assertEqual(len(run.data["steps"]), 2)
        self.assertTrue(run.data["output"]["matched"])

    def test_import_keeps_metadata_and_can_clear_graph(self):
        result = services.import_workflow(
            self.owner, self.workflow_id, {"nodes": [], "relations": []}
        )
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["nodes"], [])
        self.assertEqual(result.data["relations"], [])
        self.assertEqual(WorkflowNode.objects.filter(workflow_id=self.workflow_id).count(), 0)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 0)
        stored = Workflow.objects.get(pk=self.workflow_id)
        self.assertEqual(stored.name, "原始名称")
        self.assertEqual(stored.description, "原始描述")

    def test_import_top_level_validation(self):
        before_keys = self.workflow_node_keys(self.workflow_id)
        cases = (
            {"format": "other", "nodes": []},
            {"nodes": {}},
            {"nodes": [], "relations": "not-a-list"},
            {"nodes": [{"key": "k", "type": "start"}] * 201},
            {"nodes": [], "relations": [{}] * 501},
            None,
        )
        for document in cases:
            with self.subTest(document=document):
                result = services.import_workflow(self.owner, self.workflow_id, document)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertEqual(self.workflow_node_keys(self.workflow_id), before_keys)
        self.assertEqual(WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 1)

    def test_import_should_reject_falsy_non_list_relations(self):
        """已知缺陷：relations={} 被 falsy 默认值当成空数组，导入被放行并覆盖原图。"""
        document = {"nodes": [{"key": "k", "type": "start"}], "relations": {}}
        result = services.import_workflow(self.owner, self.workflow_id, document)
        self.assertEqual(result.code, WFStatus.PARAM_ERR)
        self.assertTrue(WorkflowNode.objects.filter(workflow_id=self.workflow_id).exists())

    def test_import_failure_keeps_existing_graph(self):
        """失败导入不得破坏原图；逐项校验当前会抛异常（已知缺陷），这里只验证回滚。"""
        before_keys = self.workflow_node_keys(self.workflow_id)
        documents = (
            {"format": "bad", "nodes": []},
            {"nodes": [{"key": "k", "type": "bogus"}]},
        )
        for document in documents:
            with self.subTest(document=document):
                try:
                    result = services.import_workflow(self.owner, self.workflow_id, document)
                    self.assertEqual(result.code, WFStatus.PARAM_ERR)
                except Exception:  # noqa: BLE001 - 逐项校验异常是已知缺陷
                    pass
                self.assertEqual(self.workflow_node_keys(self.workflow_id), before_keys)
                self.assertEqual(
                    WorkflowEdge.objects.filter(workflow_id=self.workflow_id).count(), 1
                )

    def test_import_should_return_param_err_for_invalid_items(self):
        """已知缺陷：逐项校验在事务 try 之外 raise _ImportError，未返回 PARAM_ERR。"""
        cases = (
            {"nodes": [{"key": "k", "type": "bogus"}]},
            {"nodes": [{"key": "k", "type": "start"}, {"key": "k", "type": "start"}]},
            {"nodes": [{"key": "k", "type": "start", "position": "x"}]},
            {"nodes": [{"key": "k", "type": "start", "position": {"x": "a"}}]},
            {"nodes": [{"key": "k", "type": "start", "config": [1]}]},
            {
                "nodes": [{"key": "k", "type": "start"}],
                "relations": [{"source": "k", "target": "missing"}],
            },
            {
                "nodes": [{"key": "k", "type": "start"}],
                "relations": [{"source": "k", "target": "k"}],
            },
            {
                "nodes": [
                    {"key": "a", "type": "start"},
                    {"key": "b", "type": "condition"},
                ],
                "relations": [
                    {"source": "a", "target": "b"},
                    {"source": "a", "target": "b"},
                ],
            },
        )
        for document in cases:
            with self.subTest(document=document):
                result = services.import_workflow(self.owner, self.workflow_id, document)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)

    def test_import_should_reject_cyclic_graph(self):
        """已知缺陷：导入未校验成环，循环图可被写入。"""
        document = {
            "nodes": [
                {"key": "a", "type": "start"},
                {"key": "b", "type": "condition"},
            ],
            "relations": [
                {"source": "a", "target": "b"},
                {"source": "b", "source_port": "true", "target": "a", "target_port": "in"},
            ],
        }
        result = services.import_workflow(self.owner, self.workflow_id, document)
        self.assertEqual(result.code, WFStatus.PARAM_ERR)

    def test_import_should_validate_ports(self):
        """已知缺陷：导入未校验端口合法性，任意端口都能写入。"""
        document = {
            "nodes": [
                {"key": "a", "type": "start"},
                {"key": "b", "type": "condition"},
            ],
            "relations": [
                {
                    "source": "a",
                    "source_port": "not-a-port",
                    "target": "b",
                    "target_port": "not-a-port",
                }
            ],
        }
        result = services.import_workflow(self.owner, self.workflow_id, document)
        self.assertEqual(result.code, WFStatus.PARAM_ERR)

    def test_import_should_require_exactly_one_start(self):
        """已知缺陷：导入未校验必须恰好一个 start 节点。"""
        cases = (
            {"nodes": [{"key": "b", "type": "condition"}]},
            {
                "nodes": [
                    {"key": "a", "type": "start"},
                    {"key": "b", "type": "start"},
                ]
            },
        )
        for document in cases:
            with self.subTest(document=document):
                result = services.import_workflow(self.owner, self.workflow_id, document)
                self.assertEqual(result.code, WFStatus.PARAM_ERR)


# ==================== 执行 ====================
class RunWorkflowServiceTest(WorkflowServiceTestCase):
    def test_owner_run_success_with_condition(self):
        workflow_id = self.create_workflow()
        start, condition = self.standard_graph(workflow_id)
        result = services.run_workflow(self.owner, workflow_id)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.message, "执行完成")
        self.assertEqual(result.data["status"], "success")
        self.assertEqual(result.data["error"], "")
        self.assertEqual(len(result.data["steps"]), 2)
        self.assertEqual(result.data["steps"][0]["node_key"], start["key"])
        self.assertEqual(result.data["steps"][0]["node_type"], "start")
        self.assertEqual(result.data["steps"][0]["status"], "success")
        self.assertEqual(result.data["steps"][0]["output"], {"payload": {"ok": 1}})
        self.assertEqual(result.data["steps"][1]["node_key"], condition["key"])
        self.assertEqual(result.data["steps"][1]["node_type"], "condition")
        self.assertTrue(result.data["steps"][1]["output"]["matched"])
        self.assertTrue(result.data["output"]["matched"])
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "run")
        self.assertEqual(event["payload"]["status"], "success")
        self.assertEqual(event["payload"]["steps"], 2)

    def test_editor_run_success(self):
        workflow_id = self.shared_workflow()
        self.standard_graph(workflow_id)
        result = services.run_workflow(self.editor, workflow_id)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["status"], "success")

    def test_run_permission(self):
        workflow_id = self.shared_workflow()
        self.standard_graph(workflow_id)
        self.assertEqual(services.run_workflow(self.viewer, workflow_id).code, WFStatus.FORBIDDEN)
        self.assertEqual(services.run_workflow(self.outsider, workflow_id).code, WFStatus.FORBIDDEN)
        self.assertEqual(services.run_workflow(self.owner, 999999).code, WFStatus.NOT_FOUND)

    def test_run_without_start_returns_failed_structure(self):
        workflow_id = self.create_workflow()
        self.add_node(workflow_id, "condition")
        result = services.run_workflow(self.owner, workflow_id)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.message, "执行失败")
        self.assertEqual(result.data["status"], "failed")
        self.assertIn("缺少 start", result.data["error"])
        self.assertEqual(result.data["steps"], [])
        self.assertEqual(result.data["output"], {})
        event = self.events(workflow_id)["events"][-1]
        self.assertEqual(event["op"], "run")
        self.assertEqual(event["payload"]["status"], "failed")
        self.assertEqual(event["payload"]["steps"], 0)

    def test_run_empty_workflow_returns_failed_structure(self):
        workflow_id = self.create_workflow()
        result = services.run_workflow(self.owner, workflow_id)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["status"], "failed")
        self.assertEqual(result.data["steps"], [])
        self.assertTrue(result.data["error"])


# ==================== 节点目录 ====================
class NodeCatalogServiceTest(WorkflowServiceTestCase):
    def test_list_node_types(self):
        result = services.list_node_types()
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.data["types"], NODE_TYPES)

    def test_get_node_type_meta(self):
        start = services.get_node_type_meta("start")
        self.assertTrue(start.success, start.message)
        self.assertEqual(start.data["meta"]["name"], "开始")
        self.assertEqual(start.data["meta"]["inputs"], [])
        self.assertEqual([port["id"] for port in start.data["meta"]["outputs"]], ["out"])

        condition = services.get_node_type_meta("condition")
        self.assertTrue(condition.success, condition.message)
        self.assertEqual(
            [port["id"] for port in condition.data["meta"]["outputs"]], ["true", "false"]
        )

        http = services.get_node_type_meta("http")
        self.assertEqual([port["id"] for port in http.data["meta"]["inputs"]], ["in"])
        self.assertEqual([port["id"] for port in http.data["meta"]["outputs"]], ["out"])

    def test_get_node_type_meta_not_found(self):
        for node_type in ("bogus", "", "Bad Type"):
            with self.subTest(node_type=node_type):
                result = services.get_node_type_meta(node_type)
                self.assertEqual(result.code, WFStatus.NOT_FOUND)
