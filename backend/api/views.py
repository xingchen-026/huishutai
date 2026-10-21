from django.shortcuts import render
from rest_framework import viewsets
from .models import Book
from .serializers import BookSerializer


# 创建路由列表
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer