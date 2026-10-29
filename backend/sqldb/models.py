"""sqldb 表结构定义。

本文件只描述数据库表结构：字段、约束、关联、表名、Meta。
密码哈希、参数校验、业务流程等逻辑一律不写在这里，由上层应用负责。
"""

from django.db import models


class User(models.Model):
    """用户表"""

    username = models.CharField(max_length=50, unique=True, verbose_name="用户名")
    password = models.CharField(max_length=128, verbose_name="密码")

    class Meta:
        db_table = "user"  # 指定数据库表名
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.username


class UserInfo(models.Model):
    """用户信息表"""

    GENDER_CHOICES = (
        ("male", "男"),
        ("female", "女"),
        ("unknown", "未知"),
    )

    # 一对一关联用户表（“用户名”通过 user.username 获取）
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="info", verbose_name="用户"
    )
    email = models.EmailField(max_length=100, verbose_name="邮箱")
    phone = models.CharField(max_length=20, verbose_name="手机号")
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, default="unknown", verbose_name="性别"
    )

    class Meta:
        db_table = "user_info"
        verbose_name = "用户信息"
        verbose_name_plural = verbose_name


class UploadedFile(models.Model):
    """上传文件元数据表。

    文件本体在 MinIO 对象存储中，本表记录 bucket + object_key、
    内容哈希、归属用户等元数据；不存文件内容，也不存服务器文件系统路径。
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="uploaded_files",
        verbose_name="归属用户",
    )
    original_name = models.CharField(max_length=255, verbose_name="原始文件名")
    bucket = models.CharField(max_length=63, verbose_name="对象存储 bucket")
    object_key = models.CharField(max_length=512, verbose_name="对象键（存储路径）")
    file_hash = models.CharField(max_length=64, db_index=True, verbose_name="文件 SHA-256")
    file_size = models.BigIntegerField(verbose_name="文件大小（字节）")
    content_type = models.CharField(
        max_length=128, blank=True, default="", verbose_name="MIME 类型"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        db_table = "uploaded_file"
        verbose_name = "上传文件"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "file_hash"], name="uploaded_user_hash_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["bucket", "object_key"], name="uniq_uploaded_object"),
        ]


class LLMProviderConfig(models.Model):
    """用户配置的大模型供应商接入信息（API Key 加密存储）。"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="llm_providers",
        verbose_name="归属用户",
    )
    template_code = models.CharField(max_length=64, verbose_name="供应商模板")
    name = models.CharField(max_length=100, verbose_name="配置名称")
    protocol = models.CharField(max_length=20, verbose_name="接口协议")
    base_url = models.CharField(max_length=500, verbose_name="供应商地址")
    api_key_encrypted = models.TextField(blank=True, default="", verbose_name="加密后的 API Key")
    api_key_masked = models.CharField(
        max_length=64, blank=True, default="", verbose_name="脱敏 API Key"
    )
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name="最近同步时间")
    last_sync_error = models.CharField(
        max_length=500, blank=True, default="", verbose_name="最近同步失败原因"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "llm_provider_config"
        verbose_name = "大模型供应商配置"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_llm_provider_name"),
        ]


class LLMModel(models.Model):
    """从供应商在线拉取、或用户手动登记的模型（含调用参数规格）。"""

    provider = models.ForeignKey(
        LLMProviderConfig,
        on_delete=models.CASCADE,
        related_name="models",
        verbose_name="供应商配置",
    )
    model_id = models.CharField(max_length=200, verbose_name="供应商模型 ID")
    display_name = models.CharField(max_length=200, blank=True, default="", verbose_name="展示名称")
    category = models.CharField(max_length=20, default="chat", verbose_name="模型分类")
    param_spec = models.JSONField(default=list, blank=True, verbose_name="调用参数规格")
    source = models.CharField(max_length=10, default="auto", verbose_name="来源（auto/manual）")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    raw = models.JSONField(default=dict, blank=True, verbose_name="供应商原始信息")
    synced_at = models.DateTimeField(null=True, blank=True, verbose_name="最近拉取时间")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "llm_model"
        verbose_name = "大模型"
        verbose_name_plural = verbose_name
        ordering = ["category", "model_id"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "model_id"], name="uniq_llm_model"),
        ]
        indexes = [
            models.Index(fields=["provider", "category"], name="llm_model_provider_cat_idx"),
        ]
