"""python manage.py init_vectordb —— 幂等初始化向量集合。"""

from django.core.management.base import BaseCommand, CommandError

from vectordb.crud import knowledge_collection
from vectordb.enums import VDBStatus


class Command(BaseCommand):
    help = "初始化 Milvus 向量集合（已存在则跳过）"

    def handle(self, *args, **options):
        result = knowledge_collection.ensure()
        if result.code != VDBStatus.SUCCESS:
            raise CommandError(f"初始化失败：{result.message}")
        self.stdout.write(self.style.SUCCESS(f"[OK] {result.message}：{result.data}"))