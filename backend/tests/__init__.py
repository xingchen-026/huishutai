"""LLMapi 及核心接口的回归测试包。

运行方式（在 backend/ 目录下）：
    # 无 PostgreSQL 时用 SQLite 测试配置
    DJANGO_SETTINGS_MODULE=tests.settings python manage.py test tests -v 2

    # 有 PostgreSQL 时也可直接用项目配置
    python manage.py test tests -v 2
"""
