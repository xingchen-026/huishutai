from django.db import models
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.
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

    # 密码加密写入
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    # 密码校验
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
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

    def __str__(self):
        return f'{self.user.username} 的信息'