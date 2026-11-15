"""Workflow HTTP 接口测试：认证、状态码映射、参数校验、权限矩阵与事件序号。

覆盖 backend/Workflow/views.py + urls.py 挂在 /workflow/ 下的全部接口。
测试使用内存 SQLite 与测试 settings，不依赖 PostgreSQL / 外部网络。

运行（在 backend/ 目录，PowerShell）：
    $env:DJANGO_SETTINGS_MODULE = "tests.settings"
    .venv/Scripts/python.exe -B manage.py test tests.test_workflow_api -v 2
"""

from __future__ import annotations

import json

from django.test import TestCase

from sqldb.models import User
from user.auth import issue_token
from Workflow import services
from Workflow.result import WFStatus

NODE_TYPES = ["condition", "http", "llm", "start"]
WF_CODE_BY_HTTP = {
    200: int(WFStatus.SUCCESS),
    400: int(WFStatus.PARAM_ERR),
    403: int(WFStatus.FORBIDDEN),
    404: int(WFStatus.NOT_FOUND),
    409: int(WFStatus.CONFLICT),
}


def make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, password="x")


def bearer(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {issue_token(user.pk)}"}


def api(client, method: str, path: str, user: User | None = None, payload=None):
    """以 JSON 方式调用接口；payload 为 None 时不发送请求体。"""
    kwargs = {}
    if user is not None:
        kwargs.update(bearer(user))
    if payload is None:
        return getattr(client, method)(path, **kwargs)
    return getattr(client, method)(
        path, data=json.dumps(payload), content_type="application/json", **kwargs
    )


def assert_wf_response(testcase: TestCase, response, expected_http: int) -> dict:
    """断言统一响应结构 {code,message,data} 与 HTTP 状态映射。"""
    testcase.assertEqual(response.status_code, expected_http, response.content[:300])
    testcase.assertEqual(
        response["Content-Type"].split(";")[0],
        "application/json",
        response.content[:300],
    )
    body = response.json()
    testcase.assertIsInstance(body, dict, response.content[:300])
    testcase.assertEqual(set(body), {"code", "message", "data"})
    testcase.assertEqual(body["code"], WF_CODE_BY_HTTP[expected_http])
    testcase.assertIsInstance(body["message"], str)
    testcase.assertTrue(body["message"])
    return body


class WorkflowApiTestCase(TestCase):
    def setUp(self):
        self.owner = make_user("owner")
        self.editor = make_user("editor")
        self.viewer = make_user("viewer")
        self.outsider = make_user("outsider")

    # ---------- 构造辅助 ----------
    def create_workflow(self, user=None, name="接口测试工作流", description="描述"):
        result = services.create_workflow(
            user or self.owner, {"name": name, "description": description}
        )
        self.assertTrue(result.success, result.message)
        return result.data["workflow"]["id"]

    def shared_workflow(self, name="共享工作流"):
        workflow_id = self.create_workflow(name=name)
        for user, role in ((self.editor, "editor"), (self.viewer, "viewer")):
            result = services.add_member(
                self.owner, workflow_id, {"username": user.username, "role": role}
            )
            self.assertTrue(result.success, result.message)
        return workflow_id

    def add_start_condition(self, workflow_id, payload='{"ok": 1}'):
        start = services.add_node(
            self.owner,
            workflow_id,
            {"node_type": "start", "position": {"x": 1, "y": 2}, "config": {"payload": payload}},
        )
        condition = services.add_node(
            self.owner,
            workflow_id,
            {
                "node_type": "condition",
                "position": {"x": 3, "y": 4},
                "config": {"field": "payload.ok", "operator": "eq", "value": "1"},
            },
        )
        self.assertTrue(start.success, start.message)
        self.assertTrue(condition.success, condition.message)
        relation = services.add_relation(
            self.owner,
            workflow_id,
            {
                "source_key": start.data["node"]["key"],
                "target_key": condition.data["node"]["key"],
            },
        )
        self.assertTrue(relation.success, relation.message)
        return start.data["node"], condition.data["node"]


# ==================== 认证 ====================
class WorkflowAuthApiTest(WorkflowApiTestCase):
    def test_all_endpoints_require_login(self):
        workflow_id = self.create_workflow()
        start, _condition = self.add_start_condition(workflow_id)
        edge_id = services.get_workflow(self.owner, workflow_id).data["relations"][0]["id"]
        endpoints = [
            ("get", "/workflow/workflows/"),
            ("post", "/workflow/workflows/"),
            ("get", f"/workflow/workflows/{workflow_id}/"),
            ("patch", f"/workflow/workflows/{workflow_id}/"),
            ("delete", f"/workflow/workflows/{workflow_id}/"),
            ("get", f"/workflow/workflows/{workflow_id}/events/"),
            ("post", f"/workflow/workflows/{workflow_id}/nodes/"),
            ("patch", f"/workflow/workflows/{workflow_id}/nodes/{start['key']}/"),
            ("delete", f"/workflow/workflows/{workflow_id}/nodes/{start['key']}/"),
            ("post", f"/workflow/workflows/{workflow_id}/edges/"),
            ("delete", f"/workflow/workflows/{workflow_id}/edges/{edge_id}/"),
            ("get", f"/workflow/workflows/{workflow_id}/members/"),
            ("post", f"/workflow/workflows/{workflow_id}/members/"),
            ("delete", f"/workflow/workflows/{workflow_id}/members/{self.editor.pk}/"),
            ("post", f"/workflow/workflows/{workflow_id}/import/"),
            ("get", f"/workflow/workflows/{workflow_id}/export/"),
            ("post", f"/workflow/workflows/{workflow_id}/run/"),
            ("get", "/workflow/node-types/"),
            ("get", "/workflow/node-types/start/"),
        ]
        for method, path in endpoints:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 401, (path, response.content[:200]))
                self.assertIn("detail", response.json())


# ==================== 工作流 ====================
class WorkflowApiTest(WorkflowApiTestCase):
    def test_create_and_list(self):
        created = api(
            self.client,
            "post",
            "/workflow/workflows/",
            self.owner,
            {"name": " 接口创建 ", "description": "描述"},
        )
        body = assert_wf_response(self, created, 200)
        workflow = body["data"]["workflow"]
        self.assertEqual(workflow["name"], "接口创建")
        self.assertEqual(workflow["role"], "owner")
        self.assertEqual(workflow["node_count"], 0)
        self.assertEqual(workflow["owner_name"], "owner")

        listing = api(self.client, "get", "/workflow/workflows/", self.owner)
        body = assert_wf_response(self, listing, 200)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual(body["data"]["workflows"][0]["id"], workflow["id"])

        empty = api(self.client, "get", "/workflow/workflows/", self.outsider)
        body = assert_wf_response(self, empty, 200)
        self.assertEqual(body["data"]["total"], 0)

    def test_create_validation_400(self):
        cases = ({}, {"name": ""}, {"name": "   "}, {"name": None})
        for payload in cases:
            with self.subTest(payload=payload):
                response = api(self.client, "post", "/workflow/workflows/", self.owner, payload)
                body = assert_wf_response(self, response, 400)
                self.assertIn("名称不能为空", body["message"])
        self.assertFalse(services.list_workflows(self.owner).data["workflows"])

    def test_detail_get_patch_delete_lifecycle(self):
        workflow_id = self.create_workflow(name="生命周期")
        self.add_start_condition(workflow_id)

        detail = api(self.client, "get", f"/workflow/workflows/{workflow_id}/", self.owner)
        body = assert_wf_response(self, detail, 200)
        self.assertEqual(
            set(body["data"]),
            {"workflow", "nodes", "relations", "members", "last_event_seq", "node_types"},
        )
        self.assertEqual(len(body["data"]["nodes"]), 2)
        self.assertEqual(len(body["data"]["relations"]), 1)

        patched = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/",
            self.owner,
            {"name": "改名后", "description": "新描述"},
        )
        body = assert_wf_response(self, patched, 200)
        self.assertEqual(body["data"]["workflow"]["name"], "改名后")

        deleted = api(self.client, "delete", f"/workflow/workflows/{workflow_id}/", self.owner)
        body = assert_wf_response(self, deleted, 200)
        self.assertEqual(body["data"]["id"], workflow_id)

        after = api(self.client, "get", f"/workflow/workflows/{workflow_id}/", self.owner)
        assert_wf_response(self, after, 404)

    def test_detail_not_found_404(self):
        for method, payload in (
            ("get", None),
            ("patch", {"name": "x"}),
            ("delete", None),
        ):
            with self.subTest(method=method):
                response = api(
                    self.client, method, "/workflow/workflows/999999/", self.owner, payload
                )
                body = assert_wf_response(self, response, 404)
                self.assertIn("工作流不存在", body["message"])

    def test_method_not_allowed_405(self):
        workflow_id = self.create_workflow()
        cases = (
            ("put", "/workflow/workflows/", {}),
            ("delete", "/workflow/workflows/", None),
            ("post", f"/workflow/workflows/{workflow_id}/", {}),
            ("put", f"/workflow/workflows/{workflow_id}/nodes/", {}),
            ("get", f"/workflow/workflows/{workflow_id}/run/", None),
            ("post", f"/workflow/workflows/{workflow_id}/export/", {}),
        )
        for method, path, payload in cases:
            with self.subTest(method=method, path=path):
                response = api(self.client, method, path, self.owner, payload)
                self.assertEqual(response.status_code, 405, response.content[:200])

    def test_non_dict_json_body_does_not_crash(self):
        workflow_id = self.create_workflow()
        response = api(
            self.client, "post", "/workflow/workflows/", self.owner, ["not", "an", "object"]
        )
        assert_wf_response(self, response, 400)

        response = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/",
            self.owner,
            ["not", "an", "object"],
        )
        assert_wf_response(self, response, 400)

        response = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            [],
        )
        assert_wf_response(self, response, 400)

        # 已知实现把非对象 body 归一成 {}，空用户名走"用户不存在"，返回 404 而非 400
        response = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            ["not", "an", "object"],
        )
        assert_wf_response(self, response, 404)

    def test_malformed_json_body_400(self):
        response = self.client.post(
            "/workflow/workflows/",
            data="{not-json",
            content_type="application/json",
            **bearer(self.owner),
        )
        self.assertEqual(response.status_code, 400, response.content[:200])
        self.assertIn("detail", response.json())


# ==================== 成员 ====================
class MemberApiTest(WorkflowApiTestCase):
    def test_members_get_and_add_validation(self):
        workflow_id = self.create_workflow()
        listing = api(self.client, "get", f"/workflow/workflows/{workflow_id}/members/", self.owner)
        body = assert_wf_response(self, listing, 200)
        self.assertEqual(
            [(item["username"], item["role"]) for item in body["data"]["members"]],
            [("owner", "owner")],
        )

        added = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            {"username": "editor", "role": "editor"},
        )
        body = assert_wf_response(self, added, 200)
        self.assertEqual(len(body["data"]["members"]), 2)

        duplicate = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            {"username": "editor", "role": "viewer"},
        )
        assert_wf_response(self, duplicate, 400)

        unknown = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            {"username": "ghost", "role": "editor"},
        )
        assert_wf_response(self, unknown, 404)

        add_owner = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            {"username": "owner", "role": "editor"},
        )
        assert_wf_response(self, add_owner, 400)

        bad_role = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            {"username": "viewer", "role": "admin"},
        )
        assert_wf_response(self, bad_role, 400)

    def test_add_member_requires_owner(self):
        workflow_id = self.shared_workflow()
        payload = {"username": "outsider", "role": "editor"}
        for user in (self.editor, self.viewer):
            with self.subTest(user=user.username):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{workflow_id}/members/",
                    user,
                    payload,
                )
                assert_wf_response(self, response, 403)

    def test_remove_member(self):
        workflow_id = self.create_workflow()
        api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/members/",
            self.owner,
            {"username": "editor", "role": "editor"},
        )
        removed = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/members/{self.editor.pk}/",
            self.owner,
        )
        body = assert_wf_response(self, removed, 200)
        self.assertEqual(len(body["data"]["members"]), 1)

        missing = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/members/{self.editor.pk}/",
            self.owner,
        )
        assert_wf_response(self, missing, 404)

        workflow_id = self.shared_workflow()
        forbidden = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/members/{self.viewer.pk}/",
            self.editor,
        )
        assert_wf_response(self, forbidden, 403)


# ==================== 节点 ====================
class NodeApiTest(WorkflowApiTestCase):
    def test_add_node_success_and_validation(self):
        workflow_id = self.create_workflow()
        created = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 1.5, "y": 2}},
        )
        body = assert_wf_response(self, created, 200)
        node = body["data"]["node"]
        self.assertEqual(node["name"], "开始")
        self.assertEqual(node["version"], 1)
        self.assertEqual(node["position"], {"x": 1.5, "y": 2.0})

        cases = (
            {"node_type": "bogus", "position": {"x": 0, "y": 0}},
            {"node_type": "start", "position": "bad"},
            {"node_type": "start", "position": {"x": "a", "y": 0}},
            {"node_type": "start", "position": {"x": 0, "y": 0}, "config": [1]},
        )
        for payload in cases:
            with self.subTest(payload=payload):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{workflow_id}/nodes/",
                    self.owner,
                    payload,
                )
                assert_wf_response(self, response, 400)

    def test_add_node_requires_edit_role(self):
        workflow_id = self.shared_workflow()
        payload = {"node_type": "start", "position": {"x": 0, "y": 0}}
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{workflow_id}/nodes/",
                    user,
                    payload,
                )
                assert_wf_response(self, response, 403)

    def test_update_node_and_version_conflict(self):
        workflow_id = self.shared_workflow()
        created = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 0, "y": 0}},
        )
        node_key = created.json()["data"]["node"]["key"]

        updated = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.owner,
            {"base_version": 1, "name": "改名"},
        )
        body = assert_wf_response(self, updated, 200)
        self.assertEqual(body["data"]["node"]["version"], 2)
        self.assertEqual(body["data"]["node"]["name"], "改名")

        conflict = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.owner,
            {"base_version": 1, "name": "冲突"},
        )
        body = assert_wf_response(self, conflict, 409)
        self.assertIn("刷新", body["message"])

        missing_version = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.owner,
            {"name": "缺版本"},
        )
        assert_wf_response(self, missing_version, 400)

        missing_node = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/nodes/missing-key/",
            self.owner,
            {"base_version": 1, "name": "x"},
        )
        assert_wf_response(self, missing_node, 404)

        forbidden = api(
            self.client,
            "patch",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.viewer,
            {"base_version": 2, "name": "viewer"},
        )
        assert_wf_response(self, forbidden, 403)

    def test_delete_node_and_permission(self):
        workflow_id = self.create_workflow()
        created = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 0, "y": 0}},
        )
        node_key = created.json()["data"]["node"]["key"]
        deleted = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.owner,
        )
        body = assert_wf_response(self, deleted, 200)
        self.assertEqual(body["data"]["key"], node_key)

        again = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.owner,
        )
        assert_wf_response(self, again, 404)

        workflow_id = self.shared_workflow()
        created = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 0, "y": 0}},
        )
        node_key = created.json()["data"]["node"]["key"]
        forbidden = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/nodes/{node_key}/",
            self.viewer,
        )
        assert_wf_response(self, forbidden, 403)

    def test_node_cross_workflow_not_found(self):
        first = self.create_workflow(name="工作流一")
        second = self.create_workflow(name="工作流二")
        created = api(
            self.client,
            "post",
            f"/workflow/workflows/{second}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 0, "y": 0}},
        )
        node_key = created.json()["data"]["node"]["key"]

        patched = api(
            self.client,
            "patch",
            f"/workflow/workflows/{first}/nodes/{node_key}/",
            self.owner,
            {"base_version": 1, "name": "x"},
        )
        assert_wf_response(self, patched, 404)

        deleted = api(
            self.client,
            "delete",
            f"/workflow/workflows/{first}/nodes/{node_key}/",
            self.owner,
        )
        assert_wf_response(self, deleted, 404)

        # 原节点仍属于第二个工作流
        detail = api(self.client, "get", f"/workflow/workflows/{second}/", self.owner)
        self.assertEqual([node["key"] for node in detail.json()["data"]["nodes"]], [node_key])


# ==================== 连线 ====================
class EdgeApiTest(WorkflowApiTestCase):
    def test_add_edge_success_and_validation(self):
        workflow_id = self.shared_workflow()
        start, condition = self.add_start_condition(workflow_id)
        condition2 = services.add_node(
            self.owner,
            workflow_id,
            {"node_type": "condition", "position": {"x": 5, "y": 6}},
        ).data["node"]
        created = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/edges/",
            self.editor,
            {"source_key": start["key"], "target_key": condition2["key"]},
        )
        body = assert_wf_response(self, created, 200)
        relation = body["data"]["relation"]
        self.assertEqual(relation["source_key"], start["key"])
        self.assertEqual(relation["target_key"], condition2["key"])

        cases = (
            ({}, 400),
            ({"source_key": start["key"]}, 400),
            ({"source_key": start["key"], "target_key": start["key"]}, 400),
            ({"source_key": start["key"], "target_key": "missing"}, 404),
            (
                {
                    "source_key": start["key"],
                    "source_port": "bad-port",
                    "target_key": condition["key"],
                },
                400,
            ),
        )
        for payload, expected in cases:
            with self.subTest(payload=payload):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{workflow_id}/edges/",
                    self.owner,
                    payload,
                )
                assert_wf_response(self, response, expected)

        duplicate = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/edges/",
            self.owner,
            {"source_key": start["key"], "target_key": condition2["key"]},
        )
        assert_wf_response(self, duplicate, 400)

        viewer = api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/edges/",
            self.viewer,
            {"source_key": start["key"], "target_key": condition["key"]},
        )
        assert_wf_response(self, viewer, 403)

    def test_delete_edge_and_cross_workflow(self):
        workflow_id = self.create_workflow()
        start, condition = self.add_start_condition(workflow_id)
        detail = api(self.client, "get", f"/workflow/workflows/{workflow_id}/", self.owner)
        edge_id = detail.json()["data"]["relations"][0]["id"]

        deleted = api(
            self.client, "delete", f"/workflow/workflows/{workflow_id}/edges/{edge_id}/", self.owner
        )
        body = assert_wf_response(self, deleted, 200)
        self.assertEqual(body["data"]["id"], edge_id)

        again = api(
            self.client, "delete", f"/workflow/workflows/{workflow_id}/edges/{edge_id}/", self.owner
        )
        assert_wf_response(self, again, 404)

        second = self.create_workflow(name="第二个工作流")
        start2, condition2 = self.add_start_condition(second)
        detail = api(self.client, "get", f"/workflow/workflows/{second}/", self.owner)
        other_edge_id = detail.json()["data"]["relations"][0]["id"]
        cross = api(
            self.client,
            "delete",
            f"/workflow/workflows/{workflow_id}/edges/{other_edge_id}/",
            self.owner,
        )
        assert_wf_response(self, cross, 404)


# ==================== 事件 ====================
class EventApiTest(WorkflowApiTestCase):
    def test_events_sequence_and_filters(self):
        workflow_id = self.create_workflow()
        first = api(self.client, "get", f"/workflow/workflows/{workflow_id}/events/", self.owner)
        body = assert_wf_response(self, first, 200)
        self.assertEqual(body["data"]["last_event_seq"], 1)
        self.assertEqual([event["op"] for event in body["data"]["events"]], ["workflow_created"])

        api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 0, "y": 0}},
        )
        second = api(self.client, "get", f"/workflow/workflows/{workflow_id}/events/", self.owner)
        body = assert_wf_response(self, second, 200)
        self.assertEqual(body["data"]["last_event_seq"], 2)
        self.assertEqual(len(body["data"]["events"]), 2)

        filtered = api(
            self.client,
            "get",
            f"/workflow/workflows/{workflow_id}/events/?after=1",
            self.owner,
        )
        body = assert_wf_response(self, filtered, 200)
        self.assertEqual([event["op"] for event in body["data"]["events"]], ["node_added"])

        limited = api(
            self.client,
            "get",
            f"/workflow/workflows/{workflow_id}/events/?limit=1",
            self.owner,
        )
        body = assert_wf_response(self, limited, 200)
        self.assertEqual(len(body["data"]["events"]), 1)

    def test_events_invalid_query_defaults(self):
        workflow_id = self.create_workflow()
        api(
            self.client,
            "post",
            f"/workflow/workflows/{workflow_id}/nodes/",
            self.owner,
            {"node_type": "start", "position": {"x": 0, "y": 0}},
        )
        response = api(
            self.client,
            "get",
            f"/workflow/workflows/{workflow_id}/events/?after=abc&limit=xyz",
            self.owner,
        )
        body = assert_wf_response(self, response, 200)
        self.assertEqual(len(body["data"]["events"]), 2)
        self.assertEqual(body["data"]["last_event_seq"], 2)

    def test_events_permission(self):
        workflow_id = self.shared_workflow()
        self.assertEqual(
            api(
                self.client, "get", f"/workflow/workflows/{workflow_id}/events/", self.viewer
            ).status_code,
            200,
        )
        forbidden = api(
            self.client, "get", f"/workflow/workflows/{workflow_id}/events/", self.outsider
        )
        assert_wf_response(self, forbidden, 403)
        missing = api(self.client, "get", "/workflow/workflows/999999/events/", self.owner)
        assert_wf_response(self, missing, 404)


# ==================== 导入 / 导出 ====================
class ImportExportApiTest(WorkflowApiTestCase):
    def setUp(self):
        super().setUp()
        self.workflow_id = self.create_workflow(name="导入导出")
        self.start, self.condition = self.add_start_condition(self.workflow_id)
        self.import_document = {
            "format": "huishutai.workflow",
            "format_version": 1,
            "name": "接口导入后",
            "description": "接口导入描述",
            "nodes": [
                {
                    "key": "api-start",
                    "type": "start",
                    "position": {"x": 1, "y": 2},
                    "config": {"payload": "{}"},
                },
                {
                    "key": "api-condition",
                    "type": "condition",
                    "position": {"x": 3, "y": 4},
                    "config": {},
                },
            ],
            "relations": [{"source": "api-start", "target": "api-condition"}],
        }

    def test_export_document(self):
        response = api(
            self.client,
            "get",
            f"/workflow/workflows/{self.workflow_id}/export/",
            self.owner,
        )
        body = assert_wf_response(self, response, 200)
        document = body["data"]
        self.assertEqual(document["format"], "huishutai.workflow")
        self.assertEqual(document["format_version"], 1)
        self.assertEqual(document["name"], "导入导出")
        self.assertEqual(len(document["nodes"]), 2)
        self.assertEqual(len(document["relations"]), 1)

        shared = self.shared_workflow(name="共享导出")
        viewer_ok = api(self.client, "get", f"/workflow/workflows/{shared}/export/", self.viewer)
        assert_wf_response(self, viewer_ok, 200)
        forbidden = api(self.client, "get", f"/workflow/workflows/{shared}/export/", self.outsider)
        assert_wf_response(self, forbidden, 403)

    def test_import_success(self):
        response = api(
            self.client,
            "post",
            f"/workflow/workflows/{self.workflow_id}/import/",
            self.owner,
            self.import_document,
        )
        body = assert_wf_response(self, response, 200)
        state = body["data"]
        self.assertEqual(state["workflow"]["name"], "接口导入后")
        self.assertEqual([node["key"] for node in state["nodes"]], ["api-start", "api-condition"])
        self.assertEqual(len(state["relations"]), 1)

        detail = api(self.client, "get", f"/workflow/workflows/{self.workflow_id}/", self.owner)
        self.assertEqual(
            [node["key"] for node in detail.json()["data"]["nodes"]],
            ["api-start", "api-condition"],
        )

    def test_import_top_level_validation_400(self):
        cases = (
            {"format": "other", "nodes": []},
            {"nodes": {}},
            {"nodes": [], "relations": "not-a-list"},
            {"nodes": [{"key": "k", "type": "start"}] * 201},
            {"nodes": [], "relations": [{}] * 501},
        )
        for document in cases:
            with self.subTest(document=document):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{self.workflow_id}/import/",
                    self.owner,
                    document,
                )
                assert_wf_response(self, response, 400)

        detail = api(self.client, "get", f"/workflow/workflows/{self.workflow_id}/", self.owner)
        self.assertEqual(
            [node["key"] for node in detail.json()["data"]["nodes"]],
            [self.start["key"], self.condition["key"]],
        )

    def test_import_requires_edit_role(self):
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{self.workflow_id}/import/",
                    user,
                    self.import_document,
                )
                assert_wf_response(self, response, 403)

    def test_import_invalid_item_should_return_400(self):
        """已知缺陷：逐项校验抛出未捕获的 _ImportError，HTTP 返回 500 而非 400。"""
        self.client.raise_request_exception = False
        try:
            response = api(
                self.client,
                "post",
                f"/workflow/workflows/{self.workflow_id}/import/",
                self.owner,
                {"nodes": [{"key": "k", "type": "bogus"}]},
            )
        finally:
            self.client.raise_request_exception = True
        self.assertEqual(response.status_code, 400, response.content[:200])


# ==================== 执行 ====================
class RunApiTest(WorkflowApiTestCase):
    def test_run_success(self):
        workflow_id = self.shared_workflow()
        self.add_start_condition(workflow_id)
        response = api(self.client, "post", f"/workflow/workflows/{workflow_id}/run/", self.editor)
        body = assert_wf_response(self, response, 200)
        self.assertEqual(body["data"]["status"], "success")
        self.assertEqual(len(body["data"]["steps"]), 2)
        self.assertTrue(body["data"]["output"]["matched"])
        events = services.list_events(self.owner, workflow_id).data["events"]
        self.assertEqual(events[-1]["op"], "run")
        self.assertEqual(events[-1]["payload"]["status"], "success")

    def test_run_without_start_returns_failed_payload(self):
        workflow_id = self.create_workflow()
        services.add_node(
            self.owner, workflow_id, {"node_type": "condition", "position": {"x": 0, "y": 0}}
        )
        response = api(self.client, "post", f"/workflow/workflows/{workflow_id}/run/", self.owner)
        body = assert_wf_response(self, response, 200)
        self.assertEqual(body["data"]["status"], "failed")
        self.assertEqual(body["data"]["steps"], [])
        self.assertTrue(body["data"]["error"])

    def test_run_permission(self):
        workflow_id = self.shared_workflow()
        self.add_start_condition(workflow_id)
        for user in (self.viewer, self.outsider):
            with self.subTest(user=user.username):
                response = api(self.client, "post", f"/workflow/workflows/{workflow_id}/run/", user)
                assert_wf_response(self, response, 403)
        missing = api(self.client, "post", "/workflow/workflows/999999/run/", self.owner)
        assert_wf_response(self, missing, 404)


# ==================== 节点类型 ====================
class NodeTypesApiTest(WorkflowApiTestCase):
    def test_node_types_and_detail(self):
        response = api(self.client, "get", "/workflow/node-types/", self.owner)
        body = assert_wf_response(self, response, 200)
        self.assertEqual(body["data"]["types"], NODE_TYPES)

        start = api(self.client, "get", "/workflow/node-types/start/", self.owner)
        body = assert_wf_response(self, start, 200)
        self.assertEqual(body["data"]["meta"]["name"], "开始")
        self.assertEqual(body["data"]["meta"]["type"], "start")

        condition = api(self.client, "get", "/workflow/node-types/condition/", self.owner)
        body = assert_wf_response(self, condition, 200)
        self.assertEqual(
            [port["id"] for port in body["data"]["meta"]["outputs"]], ["true", "false"]
        )

        for node_type in ("bogus", "bad_name"):
            with self.subTest(node_type=node_type):
                missing = api(self.client, "get", f"/workflow/node-types/{node_type}/", self.owner)
                body = assert_wf_response(self, missing, 404)
                self.assertIn("节点类型不存在", body["message"])


# ==================== 权限矩阵 ====================
class PermissionMatrixApiTest(WorkflowApiTestCase):
    def test_role_matrix_read_write_delete_member_run(self):
        workflow_id = self.shared_workflow(name="权限矩阵")
        self.add_start_condition(workflow_id)
        make_user("candidate")

        read_expected = (
            (self.owner, 200),
            (self.editor, 200),
            (self.viewer, 200),
            (self.outsider, 403),
        )
        for user, expected in read_expected:
            with self.subTest(action="read", role=user.username):
                response = api(self.client, "get", f"/workflow/workflows/{workflow_id}/", user)
                assert_wf_response(self, response, expected)

        write_expected = (
            (self.owner, 200),
            (self.editor, 200),
            (self.viewer, 403),
            (self.outsider, 403),
        )
        for user, expected in write_expected:
            with self.subTest(action="write", role=user.username):
                response = api(
                    self.client,
                    "patch",
                    f"/workflow/workflows/{workflow_id}/",
                    user,
                    {"name": f"矩阵-{user.username}"},
                )
                assert_wf_response(self, response, expected)

        for user, expected in write_expected:
            with self.subTest(action="add-node", role=user.username):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{workflow_id}/nodes/",
                    user,
                    {"node_type": "condition", "position": {"x": 0, "y": 0}},
                )
                assert_wf_response(self, response, expected)

        for user, expected in (
            (self.owner, 200),
            (self.editor, 200),
            (self.viewer, 403),
            (self.outsider, 403),
        ):
            with self.subTest(action="run", role=user.username):
                response = api(self.client, "post", f"/workflow/workflows/{workflow_id}/run/", user)
                assert_wf_response(self, response, expected)

        for user, expected in (
            (self.owner, 200),
            (self.editor, 403),
            (self.viewer, 403),
            (self.outsider, 403),
        ):
            with self.subTest(action="add-member", role=user.username):
                response = api(
                    self.client,
                    "post",
                    f"/workflow/workflows/{workflow_id}/members/",
                    user,
                    {"username": "candidate", "role": "viewer"},
                )
                assert_wf_response(self, response, expected)

        members = services.get_workflow(self.owner, workflow_id).data["members"]
        self.assertIn("candidate", [member["username"] for member in members])

        owned = self.create_workflow(name="待删除")
        deleted = api(self.client, "delete", f"/workflow/workflows/{owned}/", self.owner)
        assert_wf_response(self, deleted, 200)

        for user, expected in (
            (self.editor, 403),
            (self.viewer, 403),
            (self.outsider, 403),
        ):
            with self.subTest(action="delete", role=user.username):
                response = api(self.client, "delete", f"/workflow/workflows/{workflow_id}/", user)
                assert_wf_response(self, response, expected)
        still_there = api(self.client, "get", f"/workflow/workflows/{workflow_id}/", self.owner)
        assert_wf_response(self, still_there, 200)
