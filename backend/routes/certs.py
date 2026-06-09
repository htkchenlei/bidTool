"""
资质管理 API — Blueprint
支持证书 CRUD、文件上传/下载、分类目录树
"""
import os
import json
import uuid
import tempfile
import shutil
from flask import Blueprint, jsonify, request, send_file

certs_bp = Blueprint("certs", __name__)

# 允许的文件类型
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_PDF_EXTS = {".pdf"}
ALLOWED_EXTS = ALLOWED_IMAGE_EXTS | ALLOWED_PDF_EXTS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CERTS_FILE = os.path.join(DATA_DIR, "certs.json")
CERT_FILES_DIR = os.path.join(DATA_DIR, "cert_files")

# 确保文件存储目录存在
os.makedirs(CERT_FILES_DIR, exist_ok=True)

DEMO_CERTS = {
    "certs": [
        {
            "id": "1",
            "name": "建筑工程施工总承包一级",
            "type": "施工资质",
            "expire": "2026-12-31",
            "status": "valid",
            "issuer": "住建部",
            "category": "施工资质",
            "file_name": "",
            "file_path": "",
            "file_size": 0,
        },
        {
            "id": "2",
            "name": "ISO 9001 质量管理体系",
            "type": "管理体系",
            "expire": "2025-08-15",
            "status": "expired",
            "issuer": "中国质量认证中心",
            "category": "管理体系",
            "file_name": "",
            "file_path": "",
            "file_size": 0,
        },
        {
            "id": "3",
            "name": "安全生产许可证",
            "type": "安全许可",
            "expire": "2027-03-20",
            "status": "valid",
            "issuer": "应急管理部",
            "category": "安全许可",
            "file_name": "",
            "file_path": "",
            "file_size": 0,
        },
    ]
}


def load_certs():
    if os.path.exists(CERTS_FILE):
        try:
            with open(CERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEMO_CERTS


def save_certs(data):
    with open(CERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_category_tree(certs_list):
    """从证书列表中提取分类目录树"""
    from collections import defaultdict
    cats = defaultdict(list)
    for c in certs_list:
        cat = c.get("category", "未分类") or "未分类"
        cats[cat].append(c)
    result = []
    for cat_name, items in sorted(cats.items()):
        # 统计各状态数量
        valid_count = sum(1 for c in items if c.get("status") == "valid")
        expired_count = sum(1 for c in items if c.get("status") == "expired")
        result.append({
            "name": cat_name,
            "count": len(items),
            "valid_count": valid_count,
            "expired_count": expired_count,
        })
    return result


# ──────────────────────── 证书 CRUD ─────────────────────────────

@certs_bp.route("/api/certs", methods=["GET"])
def list_certs():
    data = load_certs()
    category = request.args.get("category", "")
    certs = data.get("certs", [])
    if category:
        certs = [c for c in certs if c.get("category", "未分类") == category]
    return jsonify({"certs": certs})


@certs_bp.route("/api/certs", methods=["POST"])
def add_cert():
    body = request.get_json(silent=True) or {}
    data = load_certs()
    cert = {
        "id": str(uuid.uuid4())[:8],
        "name": body.get("name", ""),
        "type": body.get("type", ""),
        "expire": body.get("expire", ""),
        "status": "valid",
        "issuer": body.get("issuer", ""),
        "category": body.get("category", "未分类"),
        "file_name": body.get("file_name", ""),
        "file_path": body.get("file_path", ""),
        "file_size": body.get("file_size", 0),
    }
    data["certs"].insert(0, cert)
    save_certs(data)
    return jsonify({"success": True, "cert": cert})


@certs_bp.route("/api/certs/<cert_id>", methods=["PUT"])
def update_cert(cert_id):
    body = request.get_json(silent=True) or {}
    data = load_certs()
    for c in data["certs"]:
        if c["id"] == cert_id:
            for field in ["name", "type", "expire", "status", "issuer", "category"]:
                if field in body:
                    c[field] = body[field]
            save_certs(data)
            return jsonify({"success": True, "cert": c})
    return jsonify({"success": False, "message": "证书不存在"}), 404


@certs_bp.route("/api/certs/<cert_id>", methods=["DELETE"])
def delete_cert(cert_id):
    data = load_certs()
    cert = next((c for c in data["certs"] if c["id"] == cert_id), None)
    if cert:
        # 删除关联的文件
        file_path = cert.get("file_path", "")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    data["certs"] = [c for c in data["certs"] if c["id"] != cert_id]
    save_certs(data)
    return jsonify({"success": True})


# ──────────────────────── 文件下载 ──────────────────────────────

@certs_bp.route("/api/certs/<cert_id>/download", methods=["GET"])
def download_cert_file(cert_id):
    data = load_certs()
    cert = next((c for c in data["certs"] if c["id"] == cert_id), None)
    if not cert:
        return jsonify({"success": False, "message": "证书不存在"}), 404

    file_path = cert.get("file_path", "")
    file_name = cert.get("file_name", "certificate")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "文件不存在"}), 404

    ext = os.path.splitext(file_path)[1]
    download_name = f"{cert.get('name', file_name)}{ext}"

    return send_file(
        file_path,
        as_attachment=True,
        download_name=download_name,
    )


# ──────────────────────── 分类目录树 ────────────────────────────

@certs_bp.route("/api/certs/categories", methods=["GET"])
def list_categories():
    """返回证书分类目录树（含各分类下证书数量）"""
    data = load_certs()
    tree = build_category_tree(data.get("certs", []))
    return jsonify({"categories": tree})


@certs_bp.route("/api/certs/categories", methods=["POST"])
def create_category():
    """创建新分类（只是占位，实际上分类在添加证书时使用）"""
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "分类名称不能为空"}), 400

    # 检查是否已存在同名分类
    data = load_certs()
    existing = build_category_tree(data.get("certs", []))
    if any(c["name"] == name for c in existing):
        return jsonify({"success": False, "message": "分类已存在"}), 400

    # 创建一个空分类（在分类列表中可见，但无证书时也会显示）
    # 暂时不需要额外存储，分类由证书的 category 字段驱动
    return jsonify({"success": True, "category": {"name": name, "count": 0}})


@certs_bp.route("/api/certs/categories/<path:cat_name>", methods=["PUT"])
def rename_category(cat_name):
    """重命名分类 — 更新该分类下所有证书的 category 字段"""
    body = request.get_json(silent=True) or {}
    new_name = body.get("name", "").strip()
    if not new_name:
        return jsonify({"success": False, "message": "新名称不能为空"}), 400

    data = load_certs()
    updated = 0
    for c in data["certs"]:
        if c.get("category", "未分类") == cat_name:
            c["category"] = new_name
            updated += 1
    save_certs(data)
    return jsonify({"success": True, "updated": updated})


@certs_bp.route("/api/certs/categories/<path:cat_name>", methods=["DELETE"])
def delete_category(cat_name):
    """删除分类 — 将该分类下所有证书移到「未分类」"""
    data = load_certs()
    for c in data["certs"]:
        if c.get("category", "未分类") == cat_name:
            c["category"] = "未分类"
    save_certs(data)
    return jsonify({"success": True})


# ──────────────────────── AI 识别（OCR） ─────────────────────────

@certs_bp.route("/api/certs/ocr", methods=["POST"])
def ocr_cert():
    """上传证书图片或 PDF，AI 识别后保存文件并返回结构化信息"""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "message": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        return jsonify({"success": False, "message": f"不支持的文件类型：{ext}，请上传图片（jpg/png/bmp）或 PDF"}), 400

    is_image = ext in ALLOWED_IMAGE_EXTS
    file_data = file.read()

    # ── 保存文件到磁盘 ──
    file_id = str(uuid.uuid4())[:8]
    saved_name = f"{file_id}{ext}"
    saved_path = os.path.join(CERT_FILES_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(file_data)
    file_size = os.path.getsize(saved_path)

    try:
        if is_image:
            from backend.llm_client import extract_cert_from_image
            result = extract_cert_from_image(file_data)
        else:
            import pdfplumber
            from backend.llm_client import extract_cert_from_text

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name

            try:
                text_parts = []
                with pdfplumber.open(tmp_path) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
                full_text = "\n".join(text_parts)
            finally:
                os.unlink(tmp_path)

            if not full_text.strip():
                return jsonify({
                    "success": False,
                    "message": "PDF 中未提取到文字，请尝试上传图片格式（jpg/png）并使用支持视觉的大模型",
                }), 400

            result = extract_cert_from_text(full_text)

        # 返回识别结果 + 文件信息
        return jsonify({
            "success": True,
            "data": result,
            "file": {
                "name": file.filename,
                "saved_name": saved_name,
                "path": saved_path,
                "size": file_size,
            }
        })

    except RuntimeError as e:
        # 识别失败，但文件已保存，仍返回文件信息
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"识别失败：{str(e)}"}), 500
