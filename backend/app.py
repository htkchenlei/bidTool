"""
BidTool — 投标工具 Flask 后端主程序
Blueprint 架构：文件 / 分析 / 资质 / 设置
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.routes.files import files_bp
from backend.routes.analysis import analysis_bp
from backend.routes.certs import certs_bp
from backend.routes.settings import settings_bp
from backend.routes.region import region_bp
from backend.routes.pricing import pricing_bp
from backend.routes.projects import projects_bp
from backend.routes.performance import performance_bp

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

# ── 注册 Blueprint ──────────────────────────────────────────
app.register_blueprint(files_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(certs_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(region_bp)
app.register_blueprint(pricing_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(performance_bp)


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
