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

# 允许的文件类型（仅支持图片格式）
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_EXTS = ALLOWED_IMAGE_EXTS

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
    ],
    "categories": []
}


def load_certs():
    if os.path.exists(CERTS_FILE):
        try:
            with open(CERTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 确保 categories 字段存在
                if "categories" not in data:
                    data["categories"] = []
                return data
        except Exception:
            pass
    return DEMO_CERTS


def save_certs(data):
    # 确保 categories 字段存在
    if "categories" not in data:
        data["categories"] = []
    with open(CERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_category_tree(data):
    """从证书列表和预设分类中提取分类目录树"""
    from collections import defaultdict
    certs_list = data.get("certs", [])
    cats = defaultdict(list)
    for c in certs_list:
        cat = c.get("category", "未分类") or "未分类"
        cats[cat].append(c)
    
    # 获取预设的空分类（没有证书的分类）
    preset_categories = data.get("categories", [])
    
    result = []
    # 处理有证书的分类
    for cat_name, items in sorted(cats.items()):
        valid_count = sum(1 for c in items if c.get("status") == "valid")
        expired_count = sum(1 for c in items if c.get("status") == "expired")
        result.append({
            "name": cat_name,
            "count": len(items),
            "valid_count": valid_count,
            "expired_count": expired_count,
        })
    
    # 处理空分类（没有证书的预设分类）
    existing_names = {c["name"] for c in result}
    for preset_cat in preset_categories:
        if preset_cat not in existing_names:
            result.append({
                "name": preset_cat,
                "count": 0,
                "valid_count": 0,
                "expired_count": 0,
            })
    
    # 按名称排序
    result.sort(key=lambda x: x["name"])
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
    if not cert:
        return jsonify({"success": False, "message": "证书不存在"}), 404

    errors = []

    # 1. 删除关联的文件
    file_path = cert.get("file_path", "")
    if file_path:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                errors.append(f"删除文件失败: {str(e)}")
        
        # 检查并删除空的上传目录
        try:
            upload_dir = os.path.dirname(file_path)
            if os.path.exists(upload_dir) and not os.listdir(upload_dir):
                os.rmdir(upload_dir)
        except Exception:
            pass

    # 2. 从证书列表中移除
    data["certs"] = [c for c in data["certs"] if c["id"] != cert_id]

    # 3. 检查是否有空的分类需要清理
    used_categories = set(c.get("category", "未分类") for c in data["certs"])
    if "categories" in data:
        new_categories = [cat for cat in data["categories"] 
                         if cat in used_categories or cat == "未分类"]
        data["categories"] = new_categories

    save_certs(data)

    result = {"success": True}
    if errors:
        result["warnings"] = errors
    return jsonify(result)


# ──────────────────────── 文件下载与预览 ──────────────────────────────

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


@certs_bp.route("/api/certs/file/<path:file_path>", methods=["GET"])
def preview_cert_file(file_path):
    """根据文件路径直接访问文件（用于图片预览）"""
    # 安全检查：确保文件在 CERT_FILES_DIR 目录下
    full_path = os.path.join(CERT_FILES_DIR, file_path)
    if not os.path.exists(full_path):
        return jsonify({"success": False, "message": "文件不存在"}), 404

    # 检查文件类型
    ext = os.path.splitext(full_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    if ext not in image_exts:
        return jsonify({"success": False, "message": "该文件类型不支持预览"}), 400

    return send_file(full_path)


# ──────────────────────── 分类目录树 ────────────────────────────

@certs_bp.route("/api/certs/categories", methods=["GET"])
def list_categories():
    """返回证书分类目录树（含各分类下证书数量）"""
    data = load_certs()
    tree = build_category_tree(data)
    return jsonify({"categories": tree})


@certs_bp.route("/api/certs/categories", methods=["POST"])
def create_category():
    """创建新分类并保存到预设分类列表"""
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "分类名称不能为空"}), 400

    # 检查是否已存在同名分类
    data = load_certs()
    existing = build_category_tree(data)
    if any(c["name"] == name for c in existing):
        return jsonify({"success": False, "message": "分类已存在"}), 400

    # 将新分类保存到预设分类列表
    if "categories" not in data:
        data["categories"] = []
    if name not in data["categories"]:
        data["categories"].append(name)
    save_certs(data)
    
    return jsonify({"success": True, "category": {"name": name, "count": 0}})


@certs_bp.route("/api/certs/categories/<path:cat_name>", methods=["PUT"])
def rename_category(cat_name):
    """重命名分类 — 更新该分类下所有证书的 category 字段，以及预设分类列表"""
    body = request.get_json(silent=True) or {}
    new_name = body.get("name", "").strip()
    if not new_name:
        return jsonify({"success": False, "message": "新名称不能为空"}), 400

    data = load_certs()
    updated = 0
    
    # 更新证书中的分类名
    for c in data["certs"]:
        if c.get("category", "未分类") == cat_name:
            c["category"] = new_name
            updated += 1
    
    # 更新预设分类列表中的名称
    if "categories" in data and cat_name in data["categories"]:
        idx = data["categories"].index(cat_name)
        data["categories"][idx] = new_name
    
    save_certs(data)
    return jsonify({"success": True, "updated": updated})


@certs_bp.route("/api/certs/categories/<path:cat_name>", methods=["DELETE"])
def delete_category(cat_name):
    """删除分类 — 将该分类下所有证书移到「未分类」，并从预设列表中删除"""
    data = load_certs()
    
    # 将证书移到未分类
    for c in data["certs"]:
        if c.get("category", "未分类") == cat_name:
            c["category"] = "未分类"
    
    # 从预设分类列表中删除
    if "categories" in data and cat_name in data["categories"]:
        data["categories"].remove(cat_name)
    
    save_certs(data)
    return jsonify({"success": True})


# ──────────────────────── AI 识别（OCR） ─────────────────────────

@certs_bp.route("/api/certs/ocr", methods=["POST"])
def ocr_cert():
    """上传证书图片，AI 识别后保存文件并返回结构化信息"""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "message": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        return jsonify({"success": False, "message": f"不支持的文件类型：{ext}，请上传图片（jpg/png/bmp/webp）"}), 400

    file_data = file.read()

    # ── 保存文件到磁盘 ──
    file_id = str(uuid.uuid4())[:8]
    saved_name = f"{file_id}{ext}"
    saved_path = os.path.join(CERT_FILES_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(file_data)
    file_size = os.path.getsize(saved_path)

    try:
        # 直接将图片传给大模型识别
        from backend.llm_client import extract_cert_from_image
        result = extract_cert_from_image(file_data)

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
