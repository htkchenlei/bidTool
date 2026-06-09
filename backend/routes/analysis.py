"""
招标分析 API — Blueprint
"""
import os
import json
import time
import uuid
from flask import Blueprint, jsonify, request

analysis_bp = Blueprint("analysis", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
ANALYSIS_FILE = os.path.join(DATA_DIR, "analysis.json")


def load_analysis():
    if os.path.exists(ANALYSIS_FILE):
        try:
            with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"records": []}


def save_analysis(data):
    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@analysis_bp.route("/api/analysis", methods=["GET"])
def list_analysis():
    return jsonify(load_analysis())


@analysis_bp.route("/api/analysis", methods=["POST"])
def create_analysis():
    body = request.get_json(silent=True) or {}
    data = load_analysis()
    record = {
        "id": str(uuid.uuid4())[:8],
        "title": body.get("title", "未命名分析"),
        "file": body.get("file", ""),
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "result": "",
    }
    data["records"].insert(0, record)
    save_analysis(data)
    return jsonify({"success": True, "record": record})


@analysis_bp.route("/api/analysis/<record_id>", methods=["DELETE"])
def delete_analysis(record_id):
    data = load_analysis()
    data["records"] = [r for r in data["records"] if r["id"] != record_id]
    save_analysis(data)
    return jsonify({"success": True})
