"""
报价调整 — 投标报价计算与策略调整
支持成本项录入、利润率调整、税费计算、多策略对比
"""
import json
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

pricing_bp = Blueprint("pricing", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PRICING_FILE = os.path.join(DATA_DIR, "pricing.json")

# ── 成本类别 ────────────────────────────────────────────
COST_CATEGORIES = [
    {"id": "labor", "name": "人工成本", "icon": "people"},
    {"id": "material", "name": "材料成本", "icon": "cube"},
    {"id": "equipment", "name": "设备成本", "icon": "cpu"},
    {"id": "service", "name": "服务费用", "icon": "headset"},
    {"id": "travel", "name": "差旅费用", "icon": "car"},
    {"id": "other", "name": "其他费用", "icon": "more"},
]


def load_pricing():
    """加载报价数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PRICING_FILE):
        with open(PRICING_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(PRICING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pricing(data):
    with open(PRICING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calc_project(proj):
    """根据成本项和策略计算报价汇总"""
    items = proj.get("items", [])
    subtotal = sum(float(item.get("unit_price", 0)) * float(item.get("quantity", 1)) for item in items)
    profit_rate = float(proj.get("profit_rate", 15))
    tax_rate = float(proj.get("tax_rate", 6))
    discount = float(proj.get("discount", 0))

    profit = round(subtotal * profit_rate / 100, 2)
    before_tax = subtotal + profit
    if discount > 0:
        before_tax -= round(before_tax * discount / 100, 2)
    tax = round(before_tax * tax_rate / 100, 2)
    total = round(before_tax + tax, 2)

    return {
        "subtotal": round(subtotal, 2),
        "profit": profit,
        "profit_rate": profit_rate,
        "discount": discount,
        "tax": tax,
        "tax_rate": tax_rate,
        "total": total,
    }


# ── 项目 CRUD ───────────────────────────────────────────

@pricing_bp.route("/api/pricing", methods=["GET"])
def list_projects():
    data = load_pricing()
    result = []
    for p in data:
        summary = calc_project(p)
        result.append({
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "strategy": p.get("strategy", "balanced"),
            "profit_rate": p.get("profit_rate", 15),
            "tax_rate": p.get("tax_rate", 6),
            "item_count": len(p.get("items", [])),
            "summary": summary,
            "created_at": p.get("created_at", ""),
            "updated_at": p.get("updated_at", ""),
        })
    return jsonify({"projects": result})


@pricing_bp.route("/api/pricing", methods=["POST"])
def create_project():
    data = load_pricing()
    body = request.get_json() or {}
    now = datetime.now().isoformat()

    project = {
        "id": str(uuid.uuid4())[:8],
        "name": body.get("name", "未命名报价").strip(),
        "description": body.get("description", "").strip(),
        "strategy": body.get("strategy", "balanced"),
        "profit_rate": float(body.get("profit_rate", 15)),
        "tax_rate": float(body.get("tax_rate", 6)),
        "discount": float(body.get("discount", 0)),
        "items": [],
        "created_at": now,
        "updated_at": now,
    }
    data.append(project)
    save_pricing(data)

    summary = calc_project(project)
    project["summary"] = summary
    project["item_count"] = 0
    return jsonify({"success": True, "project": project})


@pricing_bp.route("/api/pricing/<pid>", methods=["GET"])
def get_project(pid):
    data = load_pricing()
    for p in data:
        if p["id"] == pid:
            p["summary"] = calc_project(p)
            p["item_count"] = len(p.get("items", []))
            return jsonify({"success": True, "project": p})
    return jsonify({"success": False, "message": "未找到该报价项目"}), 404


@pricing_bp.route("/api/pricing/<pid>", methods=["PUT"])
def update_project(pid):
    data = load_pricing()
    for p in data:
        if p["id"] == pid:
            body = request.get_json() or {}
            for field in ["name", "description", "strategy"]:
                if field in body:
                    p[field] = body[field]
            for num_field in ["profit_rate", "tax_rate", "discount"]:
                if num_field in body:
                    p[num_field] = float(body[num_field])
            p["updated_at"] = datetime.now().isoformat()
            save_pricing(data)
            summary = calc_project(p)
            p["summary"] = summary
            p["item_count"] = len(p.get("items", []))
            return jsonify({"success": True, "project": p})
    return jsonify({"success": False, "message": "未找到该报价项目"}), 404


@pricing_bp.route("/api/pricing/<pid>", methods=["DELETE"])
def delete_project(pid):
    data = load_pricing()
    data = [p for p in data if p["id"] != pid]
    save_pricing(data)
    return jsonify({"success": True})


# ── 成本项 CRUD ─────────────────────────────────────────

@pricing_bp.route("/api/pricing/<pid>/items", methods=["POST"])
def add_item(pid):
    data = load_pricing()
    for p in data:
        if p["id"] == pid:
            body = request.get_json() or {}
            item = {
                "id": str(uuid.uuid4())[:8],
                "name": body.get("name", "").strip(),
                "category": body.get("category", "other"),
                "unit_price": float(body.get("unit_price", 0)),
                "quantity": float(body.get("quantity", 1)),
                "unit": body.get("unit", "项"),
                "note": body.get("note", "").strip(),
            }
            if not item["name"]:
                return jsonify({"success": False, "message": "成本项名称不能为空"}), 400
            p.setdefault("items", []).append(item)
            p["updated_at"] = datetime.now().isoformat()
            save_pricing(data)
            summary = calc_project(p)
            return jsonify({"success": True, "item": item, "summary": summary, "item_count": len(p["items"])})
    return jsonify({"success": False, "message": "未找到该报价项目"}), 404


@pricing_bp.route("/api/pricing/<pid>/items/<iid>", methods=["PUT"])
def update_item(pid, iid):
    data = load_pricing()
    for p in data:
        if p["id"] == pid:
            items = p.get("items", [])
            for item in items:
                if item["id"] == iid:
                    body = request.get_json() or {}
                    for field in ["name", "category", "unit", "note"]:
                        if field in body:
                            item[field] = body[field]
                    for num_field in ["unit_price", "quantity"]:
                        if num_field in body:
                            item[num_field] = float(body[num_field])
                    p["updated_at"] = datetime.now().isoformat()
                    save_pricing(data)
                    summary = calc_project(p)
                    return jsonify({"success": True, "item": item, "summary": summary, "item_count": len(items)})
            return jsonify({"success": False, "message": "未找到该成本项"}), 404
    return jsonify({"success": False, "message": "未找到该报价项目"}), 404


@pricing_bp.route("/api/pricing/<pid>/items/<iid>", methods=["DELETE"])
def delete_item(pid, iid):
    data = load_pricing()
    for p in data:
        if p["id"] == pid:
            items = p.get("items", [])
            p["items"] = [item for item in items if item["id"] != iid]
            p["updated_at"] = datetime.now().isoformat()
            save_pricing(data)
            summary = calc_project(p)
            return jsonify({"success": True, "summary": summary, "item_count": len(p["items"])})
    return jsonify({"success": False, "message": "未找到该报价项目"}), 404


@pricing_bp.route("/api/pricing/strategies", methods=["GET"])
def get_strategies():
    return jsonify({
        "strategies": [
            {"id": "aggressive", "name": "激进策略", "desc": "薄利多销，利润 5-10%，适用于竞争激烈的项目", "rate_range": [5, 10], "color": "peach"},
            {"id": "balanced", "name": "平衡策略", "desc": "兼顾利润与竞争力，利润 10-20%，适用于常规项目", "rate_range": [10, 20], "color": "purple"},
            {"id": "conservative", "name": "保守策略", "desc": "高利润空间，利润 20-35%，适用于优势项目", "rate_range": [20, 35], "color": "mint"},
        ],
        "categories": COST_CATEGORIES,
    })
