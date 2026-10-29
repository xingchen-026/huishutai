"""测试专用 settings：不依赖 PostgreSQL / MinIO / Milvus，可直接运行测试。

用法（在 backend/ 目录）：
    set DJANGO_SETTINGS_MODULE=tests.settings   # Windows PowerShell: $env:DJANGO_SETTINGS_MODULE="tests.settings"
    python manage.py test tests -v 2
"""

import logging

from cryptography.fernet import Fernet

from config.settings import *  # noqa: F401,F403

# 测试中会故意制造数据库唯一键冲突等错误场景，屏蔽业务日志保持输出干净
logging.disable(logging.CRITICAL)

# 测试用内存 SQLite，避免依赖外部 PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": ":memory:"},
    }
}

# 加速测试中的密码哈希（不影响被测业务逻辑）
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# 测试使用固定的、每次运行随机生成的 Fernet 密钥
LLMAPI_ENCRYPTION_KEY = Fernet.generate_key().decode()

# 缩短外部超时，避免测试误连真实网络
LLMAPI_HTTP_TIMEOUT = 2

# 默认允许 localhost/内网地址，便于测试 Ollama 类模板；SSRF 相关用例单独 override
LLMAPI_ALLOW_PRIVATE_BASE_URL = True
