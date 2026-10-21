FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (psycopg2 需要)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 使用 gunicorn 启动
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]