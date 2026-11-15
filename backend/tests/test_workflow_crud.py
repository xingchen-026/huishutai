"""Workflow 数据层测试：模型默认值/级联、唯一约束、查询与乐观锁。

数据库使用 tests.settings 的内存 SQLite，不依赖外部服务；
全部用例可通过 manage.py test tests.test_workflow_crud 单独复现。
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from sqldb.crud import (
    workflow_crud,
    workflow_edge_crud,
    workflow_event_crud,
    workflow_member_crud,
    workflow_node_crud,
)
from sqldb.enums import DBStatus
from sqldb.models import (
    User,
    Workflow,
    WorkflowEdge,
    WorkflowEvent,
    WorkflowMember,
    WorkflowNode,
)


def make_user(username="alice"):
    return User.objects.create(username=username, password="x")


def make_workflow(owner, name="流程"):
    result = workflow_crud.create(owner=owner, name=name)
    assert result.code == DBStatus.SUCCESS, result.message
    return result.data


def make_node(workflow, key, node_type="start", **extra):
    result = workflow_node_crud.create(workflow=workflow, key=key, node_type=node_type, **extra)
    assert result.code == DBStatus.SUCCESS, result.message
    return result.data


def make_edge(workflow, source, target, source_port="out", target_port="in"):
    result = workflow_edge_crud.create(
        workflow=workflow,
        source_key=source,
        source_port=source_port,
        target_key=target,
        target_port=target_port,
    )
    assert result.code == DBStatus.SUCCESS, result.message
    return result.data


class WorkflowModelTest(TestCase):
    """模型字段默认值、排序与级联删除。"""

    def setUp(self):
        self.user = make_user("alice")
        self.other = make_user("bob")

    def test_workflow_defaults(self):
        result = workflow_crud.create(owner=self.user, name="我的流程")
        self.assertEqual(result.code, DBStatus.SUCCESS)
        workflow = result.data
        self.assertEqual(workflow.description, "")
        self.assertEqual(workflow.owner_id, self.user.pk)
        self.assertIsNotNone(workflow.created_at)
        self.assertIsNotNone(workflow.updated_at)
        self.assertEqual(Workflow._meta.db_table, "workflow")
        self.assertEqual(Workflow._meta.ordering, ["-updated_at"])

    def test_workflow_ordering_by_updated_at_desc(self):
        first = make_workflow(self.user, "第一个")
        second = make_workflow(self.user, "第二个")
        later = timezone.now() + timedelta(seconds=10)
        workflow_crud.update(first.pk, updated_at=later)
        ids = [item.pk for item in Workflow.objects.all()]
        self.assertEqual(ids, [first.pk, second.pk])

    def test_workflow_node_field_defaults(self):
        workflow = make_workflow(self.user)
        node = make_node(workflow, "n1")
        self.assertEqual(node.version, 1)
        self.assertEqual(node.config, {})
        self.assertEqual(node.name, "")
        self.assertEqual(node.position_x, 0)
        self.assertEqual(node.position_y, 0)
        self.assertIsNotNone(node.created_at)
        self.assertIsNotNone(node.updated_at)
        self.assertEqual(WorkflowNode._meta.db_table, "workflow_node")

    def test_workflow_edge_field_defaults(self):
        workflow = make_workflow(self.user)
        edge = make_edge(workflow, "a", "b")
        self.assertEqual(edge.source_port, "out")
        self.assertEqual(edge.target_port, "in")
        self.assertEqual(WorkflowEdge._meta.db_table, "workflow_edge")

    def test_workflow_event_defaults_actor_nullable(self):
        workflow = make_workflow(self.user)
        event = workflow_event_crud.create(workflow=workflow, op="created").data
        self.assertIsNone(event.actor_id)
        self.assertEqual(event.payload, {})
        self.assertEqual(WorkflowEvent._meta.ordering, ["id"])
        self.assertEqual(WorkflowEvent._meta.db_table, "workflow_event")

    def test_workflow_member_default_role(self):
        workflow = make_workflow(self.user)
        member = workflow_member_crud.create(workflow=workflow, user=self.other).data
        self.assertEqual(member.role, "editor")
        self.assertEqual(WorkflowMember._meta.db_table, "workflow_member")

    def test_cascade_delete_workflow(self):
        workflow = make_workflow(self.user)
        make_node(workflow, "a")
        make_node(workflow, "b")
        make_edge(workflow, "a", "b")
        workflow_event_crud.create(workflow=workflow, op="created")
        workflow_member_crud.create(workflow=workflow, user=self.other)

        self.assertEqual(workflow_crud.delete(workflow.pk).code, DBStatus.SUCCESS)

        self.assertFalse(Workflow.objects.filter(pk=workflow.pk).exists())
        self.assertFalse(WorkflowNode.objects.filter(workflow_id=workflow.pk).exists())
        self.assertFalse(WorkflowEdge.objects.filter(workflow_id=workflow.pk).exists())
        self.assertFalse(WorkflowEvent.objects.filter(workflow_id=workflow.pk).exists())
        self.assertFalse(WorkflowMember.objects.filter(workflow_id=workflow.pk).exists())

    def test_cascade_delete_user_removes_owned_workflows(self):
        workflow = make_workflow(self.user)
        make_node(workflow, "a")
        make_edge(workflow, "a", "b")
        workflow_event_crud.create(workflow=workflow, op="created")
        workflow_member_crud.create(workflow=workflow, user=self.other)

        self.user.delete()

        self.assertFalse(Workflow.objects.filter(pk=workflow.pk).exists())
        self.assertFalse(WorkflowNode.objects.filter(workflow_id=workflow.pk).exists())
        self.assertFalse(WorkflowEdge.objects.filter(workflow_id=workflow.pk).exists())
        self.assertFalse(WorkflowEvent.objects.filter(workflow_id=workflow.pk).exists())
        self.assertFalse(WorkflowMember.objects.filter(workflow_id=workflow.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.other.pk).exists())

    def test_event_actor_set_null_when_actor_deleted(self):
        workflow = make_workflow(self.user)
        event = workflow_event_crud.create(workflow=workflow, actor=self.other, op="run").data
        self.other.delete()
        event.refresh_from_db()
        self.assertIsNone(event.actor_id)
        self.assertTrue(Workflow.objects.filter(pk=workflow.pk).exists())


class UniqueConstraintTest(TestCase):
    """唯一约束通过 CRUD 统一返回 DUPLICATE_ERR。"""

    def setUp(self):
        self.user = make_user("alice")
        self.workflow = make_workflow(self.user, "流程一")
        self.other_workflow = make_workflow(self.user, "流程二")

    def test_node_key_unique_within_workflow(self):
        make_node(self.workflow, "same-key")
        result = workflow_node_crud.create(
            workflow=self.workflow, key="same-key", node_type="condition"
        )
        self.assertEqual(result.code, DBStatus.DUPLICATE_ERR)
        self.assertEqual(
            WorkflowNode.objects.filter(workflow=self.workflow, key="same-key").count(),
            1,
        )

    def test_node_key_reusable_across_workflows(self):
        make_node(self.workflow, "same-key")
        result = workflow_node_crud.create(
            workflow=self.other_workflow, key="same-key", node_type="condition"
        )
        self.assertEqual(result.code, DBStatus.SUCCESS)

    def test_edge_five_tuple_unique(self):
        make_edge(self.workflow, "a", "b")
        result = workflow_edge_crud.create(
            workflow=self.workflow,
            source_key="a",
            source_port="out",
            target_key="b",
            target_port="in",
        )
        self.assertEqual(result.code, DBStatus.DUPLICATE_ERR)
        self.assertEqual(WorkflowEdge.objects.filter(workflow=self.workflow).count(), 1)

    def test_edge_different_port_allowed(self):
        make_edge(self.workflow, "a", "b", source_port="out")
        result = workflow_edge_crud.create(
            workflow=self.workflow,
            source_key="a",
            source_port="true",
            target_key="b",
            target_port="in",
        )
        self.assertEqual(result.code, DBStatus.SUCCESS)
        self.assertEqual(WorkflowEdge.objects.filter(workflow=self.workflow).count(), 2)

    def test_edge_tuple_reusable_across_workflows(self):
        make_edge(self.workflow, "a", "b")
        result = workflow_edge_crud.create(
            workflow=self.other_workflow,
            source_key="a",
            source_port="out",
            target_key="b",
            target_port="in",
        )
        self.assertEqual(result.code, DBStatus.SUCCESS)

    def test_member_unique_per_workflow_user(self):
        workflow_member_crud.create(workflow=self.workflow, user=self.user)
        result = workflow_member_crud.create(workflow=self.workflow, user=self.user)
        self.assertEqual(result.code, DBStatus.DUPLICATE_ERR)

    def test_member_same_user_different_workflows_allowed(self):
        workflow_member_crud.create(workflow=self.workflow, user=self.user)
        result = workflow_member_crud.create(workflow=self.other_workflow, user=self.user)
        self.assertEqual(result.code, DBStatus.SUCCESS)


class WorkflowListForUserTest(TestCase):
    """WorkflowCRUD.list_for_user：owner + 被邀请成员、去重、limit、排序。"""

    def setUp(self):
        self.owner = make_user("owner")
        self.member = make_user("member")
        self.outsider = make_user("outsider")
        self.other_owner = make_user("other-owner")
        self.owned = make_workflow(self.owner, "我创建的")
        self.shared = make_workflow(self.other_owner, "共享给我")
        self.hidden = make_workflow(self.other_owner, "与我无关")
        workflow_member_crud.create(workflow=self.shared, user=self.member)

    def test_owner_and_member_both_returned(self):
        owner_ids = [item.pk for item in workflow_crud.list_for_user(self.owner.pk).data]
        member_ids = [item.pk for item in workflow_crud.list_for_user(self.member.pk).data]
        self.assertEqual(owner_ids, [self.owned.pk])
        self.assertEqual(member_ids, [self.shared.pk])

    def test_no_permission_user_gets_nothing(self):
        result = workflow_crud.list_for_user(self.outsider.pk)
        self.assertEqual(result.code, DBStatus.SUCCESS)
        self.assertEqual(result.data, [])

    def test_distinct_when_owner_also_member(self):
        workflow_member_crud.create(workflow=self.owned, user=self.owner)
        ids = [item.pk for item in workflow_crud.list_for_user(self.owner.pk).data]
        self.assertEqual(ids, [self.owned.pk])

    def test_limit_lower_clamped_to_one(self):
        self.assertEqual(len(workflow_crud.list_for_user(self.owner.pk, limit=0).data), 1)
        self.assertEqual(len(workflow_crud.list_for_user(self.owner.pk, limit=-5).data), 1)

    def test_limit_upper_clamped_to_200(self):
        for index in range(200):
            make_workflow(self.owner, "批量-{0}".format(index))
        result = workflow_crud.list_for_user(self.owner.pk, limit=500)
        self.assertEqual(result.code, DBStatus.SUCCESS)
        self.assertEqual(len(result.data), 200)

    def test_order_by_updated_at_desc(self):
        later = timezone.now() + timedelta(seconds=30)
        workflow_crud.update(self.owned.pk, updated_at=later)
        ids = [item.pk for item in workflow_crud.list_for_user(self.owner.pk).data]
        self.assertEqual(ids[0], self.owned.pk)


class WorkflowNodeCRUDTest(TestCase):
    """WorkflowNodeCRUD：列表、按 key 查询、乐观锁更新、批量删除。"""

    def setUp(self):
        self.user = make_user("alice")
        self.workflow = make_workflow(self.user, "流程一")
        self.other_workflow = make_workflow(self.user, "流程二")

    def test_list_by_workflow(self):
        make_node(self.workflow, "a")
        make_node(self.workflow, "b", node_type="condition")
        make_node(self.other_workflow, "c")
        result = workflow_node_crud.list_by_workflow(self.workflow.pk)
        self.assertEqual(result.code, DBStatus.SUCCESS)
        self.assertEqual({node.key for node in result.data}, {"a", "b"})

    def test_get_by_key_and_cross_workflow_miss(self):
        make_node(self.workflow, "a")
        found = workflow_node_crud.get_by_key(self.workflow.pk, "a")
        self.assertEqual(found.code, DBStatus.SUCCESS)
        self.assertEqual(found.data.key, "a")
        missed = workflow_node_crud.get_by_key(self.other_workflow.pk, "a")
        self.assertEqual(missed.code, DBStatus.NOT_FOUND)

    def test_update_if_version_success(self):
        node = make_node(self.workflow, "a")
        # 先改成较早时间，避免 Windows 时钟精度导致新旧 updated_at 落在同一 tick。
        old_updated_at = timezone.now() - timedelta(hours=1)
        WorkflowNode.objects.filter(pk=node.pk).update(updated_at=old_updated_at)

        result = workflow_node_crud.update_if_version(
            self.workflow.pk, "a", 1, name="新名称", config={"payload": '{"a": 1}'}
        )
        self.assertEqual(result.code, DBStatus.SUCCESS)
        updated = result.data
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.name, "新名称")
        self.assertEqual(updated.config, {"payload": '{"a": 1}'})
        self.assertGreater(updated.updated_at, old_updated_at)
        node.refresh_from_db()
        self.assertEqual(node.version, 2)
        self.assertGreater(node.updated_at, old_updated_at)

    def test_update_if_version_conflict(self):
        make_node(self.workflow, "a")
        first = workflow_node_crud.update_if_version(self.workflow.pk, "a", 1, name="v2")
        self.assertEqual(first.code, DBStatus.SUCCESS)
        stale = workflow_node_crud.update_if_version(self.workflow.pk, "a", 1, name="v2-again")
        self.assertEqual(stale.code, DBStatus.CONFLICT)
        self.assertIn("请刷新", stale.message)
        self.assertEqual(workflow_node_crud.get_by_key(self.workflow.pk, "a").data.name, "v2")

    def test_update_if_version_node_not_found(self):
        result = workflow_node_crud.update_if_version(self.workflow.pk, "missing", 1, name="x")
        self.assertEqual(result.code, DBStatus.NOT_FOUND)

    def test_update_if_version_requires_fields(self):
        make_node(self.workflow, "a")
        with self.assertRaisesMessage(ValueError, "至少需要一个待更新字段"):
            workflow_node_crud.update_if_version(self.workflow.pk, "a", 1)

    def test_delete_by_workflow(self):
        make_node(self.workflow, "a")
        make_node(self.workflow, "b")
        make_node(self.other_workflow, "c")
        self.assertEqual(
            workflow_node_crud.delete_by_workflow(self.workflow.pk).code,
            DBStatus.SUCCESS,
        )
        self.assertFalse(WorkflowNode.objects.filter(workflow=self.workflow).exists())
        self.assertTrue(WorkflowNode.objects.filter(workflow=self.other_workflow, key="c").exists())


class WorkflowEdgeCRUDTest(TestCase):
    """WorkflowEdgeCRUD：列表、按工作流/节点 key 清理连线。"""

    def setUp(self):
        self.user = make_user("alice")
        self.workflow = make_workflow(self.user, "流程一")
        self.other_workflow = make_workflow(self.user, "流程二")

    def test_list_by_workflow(self):
        make_edge(self.workflow, "a", "b")
        make_edge(self.other_workflow, "x", "y")
        result = workflow_edge_crud.list_by_workflow(self.workflow.pk)
        self.assertEqual(result.code, DBStatus.SUCCESS)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].source_key, "a")

    def test_delete_by_workflow_only_target(self):
        make_edge(self.workflow, "a", "b")
        make_edge(self.other_workflow, "a", "b")
        self.assertEqual(
            workflow_edge_crud.delete_by_workflow(self.workflow.pk).code,
            DBStatus.SUCCESS,
        )
        self.assertFalse(WorkflowEdge.objects.filter(workflow=self.workflow).exists())
        self.assertEqual(WorkflowEdge.objects.filter(workflow=self.other_workflow).count(), 1)

    def test_delete_by_node_key_cleans_both_directions(self):
        make_edge(self.workflow, "n1", "n2")
        make_edge(self.workflow, "n2", "n3")
        make_edge(self.workflow, "n3", "n4")
        make_edge(self.other_workflow, "n1", "n2")

        self.assertEqual(
            workflow_edge_crud.delete_by_node_key(self.workflow.pk, "n2").code,
            DBStatus.SUCCESS,
        )

        remaining = {
            (edge.source_key, edge.target_key)
            for edge in WorkflowEdge.objects.filter(workflow=self.workflow)
        }
        self.assertEqual(remaining, {("n3", "n4")})
        self.assertEqual(WorkflowEdge.objects.filter(workflow=self.other_workflow).count(), 1)


class WorkflowEventCRUDTest(TestCase):
    """WorkflowEventCRUD：增量拉取与最新序号。"""

    def setUp(self):
        self.user = make_user("alice")
        self.workflow = make_workflow(self.user, "流程一")
        self.other_workflow = make_workflow(self.user, "流程二")

    def test_list_after_filters_orders_and_scopes(self):
        first = workflow_event_crud.create(workflow=self.workflow, op="one").data
        second = workflow_event_crud.create(workflow=self.workflow, op="two").data
        third = workflow_event_crud.create(workflow=self.workflow, op="three").data
        workflow_event_crud.create(workflow=self.other_workflow, op="other")

        all_ids = [event.pk for event in workflow_event_crud.list_after(self.workflow.pk).data]
        self.assertEqual(all_ids, [first.pk, second.pk, third.pk])

        after_first = [
            event.pk for event in workflow_event_crud.list_after(self.workflow.pk, first.pk).data
        ]
        self.assertEqual(after_first, [second.pk, third.pk])

    def test_list_after_limit_lower_clamped_to_one(self):
        workflow_event_crud.create(workflow=self.workflow, op="one")
        workflow_event_crud.create(workflow=self.workflow, op="two")
        self.assertEqual(len(workflow_event_crud.list_after(self.workflow.pk, 0, limit=0).data), 1)
        self.assertEqual(len(workflow_event_crud.list_after(self.workflow.pk, 0, limit=-3).data), 1)

    def test_list_after_limit_upper_clamped_to_200(self):
        for index in range(201):
            workflow_event_crud.create(workflow=self.workflow, op="op", payload={"i": index})
        result = workflow_event_crud.list_after(self.workflow.pk, 0, limit=500)
        self.assertEqual(result.code, DBStatus.SUCCESS)
        self.assertEqual(len(result.data), 200)

    def test_latest_id_empty_and_max(self):
        self.assertEqual(workflow_event_crud.latest_id(self.workflow.pk).data, 0)
        workflow_event_crud.create(workflow=self.workflow, op="one")
        last = workflow_event_crud.create(workflow=self.workflow, op="two").data
        self.assertEqual(workflow_event_crud.latest_id(self.workflow.pk).data, last.pk)
