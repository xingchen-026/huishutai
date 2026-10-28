"""python manage.py init_storage —— 检查 MinIO 连接并创建 bucket（幂等）。"""

from django.core.management.base import BaseCommand, CommandError

import filestorage


class Command(BaseCommand):
    help = "初始化文件对象存储：检查 MinIO 连接并创建 bucket（幂等）"

    def handle(self, *args, **options):
        try:
            filestorage.ensure_bucket()
            info = filestorage.health_check()
        except filestorage.StorageError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] MinIO {info['endpoint']} bucket={info['bucket']} "
                f"buckets={info['buckets']}"
            )
        )