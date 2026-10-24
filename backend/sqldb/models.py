"""sqldb 表结构定义。

本文件只描述数据库表结构：字段、约束、关联、表名、Meta。
密码哈希、参数校验、业务流程等逻辑一律不写在这里，由上层应用负责。
"""

from django.db import models

class User(models.Model):
    """用户表"""
    username = models.CharField(
        max_length=50, unique=True, verbose_name='用户名'
    )
    password = models.CharField(
        max_length=128, verbose_name='密码'
    )

    class Meta:
        db_table = 'user'          # 指定数据库表名
        verbose_name = '用户'
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
        ('male', '男'),
        ('female', '女'),
        ('unknown', '未知'),
    )

    # 一对一关联用户表（“用户名”通过 user.username 获取）
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='info',
        verbose_name='用户'
    )
    email = models.EmailField(max_length=100, verbose_name='邮箱')
    phone = models.CharField(max_length=20, verbose_name='手机号')
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='unknown',
        verbose_name='性别'
    )

    class Meta:
        db_table = 'user_info'
        verbose_name = '用户信息'
        verbose_name_plural = verbose_name
        