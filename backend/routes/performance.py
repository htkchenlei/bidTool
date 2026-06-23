"""
业绩管理 API — Blueprint
支持业绩 CRUD、PDF 文件上传/下载、水印添加、多字段筛选
"""
import os
import json
import uuid
import tempfile
import io
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file

performance_bp = Blueprint("performance", __name__)

# 允许的文件类型（仅支持 PDF）
ALLOWED_EXTS = {".pdf"}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
PERF_FILE = os.path.join(DATA_DIR, "performance.json")
PERF_FILES_DIR = os.path.join(DATA_DIR, "performance_files")

# 确保文件存储目录存在
os.makedirs(PERF_FILES_DIR, exist_ok=True)


def load_performances():
    if os.path.exists(PERF_FILE):
        try:
            with open(PERF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"performances": []}


def save_performances(data):
    with open(PERF_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────── 业绩 CRUD ─────────────────────────────

@performance_bp.route("/api/performances", methods=["GET"])
def list_performances():
    data = load_performances()
    items = data.get("performances", [])

    # 多字段筛选
    keyword = request.args.get("keyword", "").strip()
    party_b = request.args.get("party_b", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    category = request.args.get("category", "").strip()
    has_file = request.args.get("has_file", "").strip()

    if keyword:
        kw = keyword.lower()
        items = [p for p in items if kw in p.get("project_name", "").lower()
                 or kw in p.get("party_b", "").lower()
                 or kw in p.get("description", "").lower()]
    if party_b:
        pb = party_b.lower()
        items = [p for p in items if pb in p.get("party_b", "").lower()]
    if category:
        items = [p for p in items if p.get("category", "") == category]
    if date_from:
        items = [p for p in items if p.get("date", "") >= date_from]
    if date_to:
        items = [p for p in items if p.get("date", "") <= date_to]
    if has_file == "yes":
        items = [p for p in items if p.get("file_path", "")]
    elif has_file == "no":
        items = [p for p in items if not p.get("file_path", "")]

    return jsonify({"performances": items})


@performance_bp.route("/api/performances", methods=["POST"])
def add_performance():
    body = request.get_json(silent=True) or {}
    data = load_performances()
    item = {
        "id": str(uuid.uuid4())[:8],
        "project_name": body.get("project_name", ""),
        "party_b": body.get("party_b", ""),
        "date": body.get("date", ""),
        "category": body.get("category", "未分类"),
        "amount": body.get("amount", ""),
        "description": body.get("description", ""),
        "file_name": body.get("file_name", ""),
        "file_path": body.get("file_path", ""),
        "file_size": body.get("file_size", 0),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["performances"].insert(0, item)
    save_performances(data)
    return jsonify({"success": True, "performance": item})


@performance_bp.route("/api/performances/<perf_id>", methods=["PUT"])
def update_performance(perf_id):
    body = request.get_json(silent=True) or {}
    data = load_performances()
    for p in data["performances"]:
        if p["id"] == perf_id:
            for field in ["project_name", "party_b", "date", "category",
                          "amount", "description", "file_name", "file_path", "file_size"]:
                if field in body:
                    p[field] = body[field]
            save_performances(data)
            return jsonify({"success": True, "performance": p})
    return jsonify({"success": False, "message": "业绩不存在"}), 404


@performance_bp.route("/api/performances/<perf_id>", methods=["DELETE"])
def delete_performance(perf_id):
    data = load_performances()
    perf = next((p for p in data["performances"] if p["id"] == perf_id), None)
    if not perf:
        return jsonify({"success": False, "message": "业绩不存在"}), 404

    # 删除关联文件
    file_path = perf.get("file_path", "")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    data["performances"] = [p for p in data["performances"] if p["id"] != perf_id]
    save_performances(data)
    return jsonify({"success": True})


# ──────────────────────── 文件上传 ──────────────────────────────

@performance_bp.route("/api/performances/upload", methods=["POST"])
def upload_performance_file():
    """上传合同扫描件 PDF"""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "message": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        return jsonify({"success": False, "message": f"不支持的文件类型：{ext}，仅支持 PDF"}), 400

    file_data = file.read()
    file_id = str(uuid.uuid4())[:8]
    saved_name = f"{file_id}{ext}"
    saved_path = os.path.join(PERF_FILES_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(file_data)
    file_size = os.path.getsize(saved_path)

    return jsonify({
        "success": True,
        "file": {
            "name": file.filename,
            "saved_name": saved_name,
            "path": saved_path,
            "size": file_size,
        }
    })


# ──────────────────────── 文件下载（支持水印） ──────────────────

@performance_bp.route("/api/performances/<perf_id>/download", methods=["GET"])
def download_performance_file(perf_id):
    data = load_performances()
    perf = next((p for p in data["performances"] if p["id"] == perf_id), None)
    if not perf:
        return jsonify({"success": False, "message": "业绩不存在"}), 404

    file_path = perf.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "文件不存在"}), 404

    watermark = request.args.get("watermark", "").strip()
    download_name = f"{perf.get('project_name', 'performance')}.pdf"

    if watermark:
        try:
            watermarked_bytes = _add_watermark(file_path, watermark)
            return send_file(
                io.BytesIO(watermarked_bytes),
                as_attachment=True,
                download_name=download_name,
                mimetype="application/pdf",
            )
        except Exception as e:
            # 水印添加失败，返回原文件
            pass

    return send_file(file_path, as_attachment=True, download_name=download_name)


# ──────────────────────── 批量下载（支持水印） ──────────────────

@performance_bp.route("/api/performances/batch-download", methods=["POST"])
def batch_download():
    """批量下载多个业绩文件，打包为 ZIP（支持水印）"""
    body = request.get_json(silent=True) or {}
    ids = body.get("ids", [])
    watermark = body.get("watermark", "").strip()

    if not ids:
        return jsonify({"success": False, "message": "请选择要下载的业绩"}), 400

    data = load_performances()
    perfs = [p for p in data["performances"] if p["id"] in ids and p.get("file_path")]

    if not perfs:
        return jsonify({"success": False, "message": "没有可下载的文件"}), 404

    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for perf in perfs:
            file_path = perf.get("file_path", "")
            if not file_path or not os.path.exists(file_path):
                continue
            # 文件名：项目名称.pdf，避免重名
            base_name = perf.get("project_name", "unnamed")
            safe_name = "".join(c for c in base_name if c not in r'\/:*?"<>|')
            file_ext = os.path.splitext(file_path)[1]
            arc_name = f"{safe_name}{file_ext}"

            if watermark:
                try:
                    watermarked_bytes = _add_watermark(file_path, watermark)
                    zf.writestr(arc_name, watermarked_bytes)
                except Exception:
                    zf.write(file_path, arc_name)
            else:
                zf.write(file_path, arc_name)

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"业绩文件_{timestamp}.zip",
        mimetype="application/zip",
    )


# ──────────────────────── 分类列表 ──────────────────────────────

@performance_bp.route("/api/performances/categories", methods=["GET"])
def list_categories():
    data = load_performances()
    cats = set()
    for p in data.get("performances", []):
        cat = p.get("category", "未分类") or "未分类"
        cats.add(cat)
    return jsonify({"categories": sorted(cats)})


# ──────────────────────── PDF 水印 ──────────────────────────────

def _add_watermark(pdf_path, watermark_text):
    """为 PDF 文件添加对角线水印，返回带水印的 PDF 字节"""
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        raise RuntimeError("缺少依赖：请安装 PyPDF2 和 reportlab")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # 创建水印页面
    for page in reader.pages:
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # 用 reportlab 生成水印 PDF 页
        watermark_buffer = io.BytesIO()
        c = canvas.Canvas(watermark_buffer, pagesize=(page_width, page_height))
        c.saveState()

        # 半透明对角线水印
        c.setFillAlpha(0.12)
        c.setFont("Helvetica-Bold", 36)
        c.setFillColorRGB(0.5, 0.5, 0.5)

        # 多行水印覆盖
        for y_offset in range(-1, int(page_height / 150) + 2):
            for x_offset in range(-1, int(page_width / 300) + 2):
                x = x_offset * 300
                y = y_offset * 150
                c.saveState()
                c.translate(x, y)
                c.rotate(30)
                c.drawString(0, 0, watermark_text)
                c.restoreState()

        c.restoreState()
        c.save()
        watermark_buffer.seek(0)

        # 合并水印到原页面
        watermark_reader = PdfReader(watermark_buffer)
        watermark_page = watermark_reader.pages[0]
        watermark_page.merge_page(page)
        writer.add_page(watermark_page)

    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    return output_buffer.getvalue()
