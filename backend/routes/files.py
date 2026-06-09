"""
文件管理 API — Blueprint
支持文件上传、文件夹管理
"""
import os
import shutil
from flask import Blueprint, jsonify, request

files_bp = Blueprint("files", __name__)

FILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "files")
os.makedirs(FILES_DIR, exist_ok=True)


def _list_path(dir_path):
    """列出指定目录下的文件和文件夹"""
    items = {"folders": [], "files": []}
    if not os.path.exists(dir_path):
        return items
    for name in os.listdir(dir_path):
        fpath = os.path.join(dir_path, name)
        stat = os.stat(fpath)
        if os.path.isdir(fpath):
            items["folders"].append({
                "name": name,
                "modified": stat.st_mtime,
                "type": "FOLDER",
            })
        else:
            items["files"].append({
                "name": name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "type": os.path.splitext(name)[1].lstrip(".").upper() or "FILE",
            })
    items["folders"].sort(key=lambda x: x["name"].lower())
    items["files"].sort(key=lambda x: x["modified"], reverse=True)
    return items


@files_bp.route("/api/files", methods=["GET"])
def list_files():
    folder = request.args.get("folder", "")
    # 安全检查：防止路径穿越
    if ".." in folder or folder.startswith("/"):
        return jsonify({"error": "非法路径"}), 400
    target = os.path.join(FILES_DIR, folder) if folder else FILES_DIR
    result = _list_path(target)
    result["current_folder"] = folder
    return jsonify(result)


@files_bp.route("/api/files/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "未找到文件"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"success": False, "message": "文件名为空"}), 400
    folder = request.form.get("folder", "")
    target_dir = os.path.join(FILES_DIR, folder) if folder else FILES_DIR
    os.makedirs(target_dir, exist_ok=True)
    save_path = os.path.join(target_dir, f.filename)
    f.save(save_path)
    return jsonify({"success": True, "message": f"文件 {f.filename} 上传成功"})


@files_bp.route("/api/files/folder", methods=["POST"])
def create_folder():
    data = request.get_json() or {}
    folder_name = data.get("name", "").strip()
    if not folder_name:
        return jsonify({"success": False, "message": "文件夹名不能为空"}), 400
    if ".." in folder_name or "/" in folder_name or "\\" in folder_name:
        return jsonify({"success": False, "message": "文件夹名包含非法字符"}), 400
    parent = data.get("parent", "")
    target_dir = os.path.join(FILES_DIR, parent, folder_name) if parent else os.path.join(FILES_DIR, folder_name)
    if os.path.exists(target_dir):
        return jsonify({"success": False, "message": "文件夹已存在"}), 409
    os.makedirs(target_dir)
    return jsonify({"success": True, "message": f"文件夹 {folder_name} 创建成功"})


@files_bp.route("/api/files/folder/<path:foldername>", methods=["DELETE"])
def delete_folder(foldername):
    fpath = os.path.join(FILES_DIR, foldername)
    if not os.path.exists(fpath) or not os.path.isdir(fpath):
        return jsonify({"success": False, "message": "文件夹不存在"}), 404
    shutil.rmtree(fpath)
    return jsonify({"success": True, "message": "文件夹已删除"})


@files_bp.route("/api/files/<path:filename>", methods=["DELETE"])
def delete_file(filename):
    fpath = os.path.join(FILES_DIR, filename)
    if os.path.exists(fpath) and os.path.isfile(fpath):
        os.remove(fpath)
        return jsonify({"success": True, "message": "文件已删除"})
    return jsonify({"success": False, "message": "文件不存在"}), 404
