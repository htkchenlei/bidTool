# BidTool 应用镜像
# 基于 bidtool-base:latest（需先构建基础镜像，构建一次即可复用）
#
# 首次部署：
#   docker build -f Dockerfile.base -t bidtool-base:latest .
#   docker-compose up -d --build
#
# 后续更新（业务代码改动，秒级完成）：
#   docker-compose up -d --build

# ==================== 基于预构建的基础镜像 ====================
FROM bidtool-base:latest

WORKDIR /app

# 复制后端源码
COPY backend/ ./backend/

# 复制前端源码（纯静态，无需构建）
COPY frontend/ ./frontend/

# 创建数据目录（运行时通过 volume 挂载持久化）
RUN mkdir -p /app/data && chmod 777 /app/data

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PORT=5000

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# 启动命令：使用 gunicorn 生产 WSGI 服务器
# workers=2 / threads=4 适合中小并发，可按需调整
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "backend.app:app"]
