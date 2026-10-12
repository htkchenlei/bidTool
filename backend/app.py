"""
BidTool — 投标工具 Flask 后端主程序
Blueprint 架构：文件 / 分析 / 资质 / 设置
"""
import os
import sys
import time

# Windows 控制台默认 GBK 编码，强制 stdout/stderr 使用 UTF-8，避免输出含特殊字符时触发 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_from_directory, request, g
from flask_cors import CORS

from backend.app_logger import get_logger, log_info, log_error

from backend.routes.files import files_bp
from backend.routes.analysis import analysis_bp
from backend.routes.certs import certs_bp
from backend.routes.settings import settings_bp
from backend.routes.region import region_bp
from backend.routes.pricing import pricing_bp
from backend.routes.projects import projects_bp
from backend.routes.performance import performance_bp
from backend.routes.bid_check import bid_check_bp
from backend.routes.bid_score import bid_score_bp

# ── 路径配置 ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
TEMPLATE_DIR = os.path.join(FRONTEND_DIR, "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=TEMPLATE_DIR,
)
CORS(app)

# ── 操作日志中间件 ──────────────────────────────────────────
# 记录每个 API 请求：方法、路径、状态码、耗时、客户端 IP，写入日志文件并输出到控制台（docker logs 可见）
@app.before_request
def _log_request_start():
    g._req_start = time.time()


@app.after_request
def _log_request_end(resp):
    if request.path.startswith("/static/"):
        return resp
    elapsed_ms = int((time.time() - getattr(g, "_req_start", time.time())) * 1000)
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
    # 只记首段 IP，去掉代理追加的列表
    client_ip = client_ip.split(",")[0].strip()
    log_info(f"{request.method} {request.path} -> {resp.status_code} ({elapsed_ms}ms) ip={client_ip}")
    return resp


@app.errorhandler(Exception)
def _log_unhandled_error(e):
    log_error(f"未捕获异常 {request.method} {request.path}: {type(e).__name__}: {e}")
    # 保留 Flask 默认行为（debug 下展示调试页，生产返回 500）
    raise e

# ── 注册 Blueprint ──────────────────────────────────────────
app.register_blueprint(files_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(certs_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(region_bp)
app.register_blueprint(pricing_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(performance_bp)
app.register_blueprint(bid_check_bp)
app.register_blueprint(bid_score_bp)


# ── 静态页面入口 ────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(TEMPLATE_DIR, "index.html")


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)


# ── 启动 ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  BidTool — 投标工具 已启动")
    print("  访问地址：http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
