from rest_framework import serializers
from .models import Book

# 创建序列化器
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'  # 包含模型的所有字段