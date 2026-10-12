"""
设置 API — Blueprint
管理大模型的 API 配置。所有 API 接入点均为用户自定义，不提供内置默认模型，
用户通过"新建自定义模型"添加任意数量的兼容 OpenAI 格式的模型。
"""
import os
import json
from flask import Blueprint, jsonify, request

from backend.app_logger import log_error, log_info

settings_bp = Blueprint("settings", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "models": [],
    "active_model": "",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


@settings_bp.route("/api/config", methods=["GET"])
def get_config():
    cfg = load_config()
    safe_models = []
    for m in cfg.get("models", []):
        sm = m.copy()
        key = sm.get("api_key", "")
        if key and len(key) > 4:
            sm["api_key_masked"] = "*" * (len(key) - 4) + key[-4:]
        else:
            sm["api_key_masked"] = key
        safe_models.append(sm)
    return jsonify({"models": safe_models, "active_model": cfg.get("active_model", "")})


@settings_bp.route("/api/config", methods=["POST"])
def save_config_api():
    data = request.get_json(silent=True) or {}
    cfg = load_config()

    if "models" in data:
        existing = {m["id"]: m for m in cfg.get("models", [])}
        new_models = []
        for m in data["models"]:
            mid = m.get("id")
            if mid and mid in existing:
                merged = existing[mid].copy()
                merged.update({k: v for k, v in m.items() if k != "api_key_masked"})
                if m.get("api_key") and not m.get("api_key", "").startswith("*"):
                    merged["api_key"] = m["api_key"]
                new_models.append(merged)
            else:
                new_models.append(m)
        cfg["models"] = new_models

    if "active_model" in data:
        cfg["active_model"] = data["active_model"]

    save_config(cfg)
    return jsonify({"success": True, "message": "配置已保存"})


@settings_bp.route("/api/settings/test-model", methods=["POST"])
def test_model():
    """测试大模型连接 — 支持两种模式：
    1. 通过 model_id 测试已保存的模型（若请求中同时携带 api_key/base_url/model，则用表单值覆盖）
    2. 通过 api_key/base_url/model 直接测试未保存的临时配置
    """
    data = request.get_json(silent=True) or {}

    target = None
    model_id = data.get("model_id", "")
    form_api_key = (data.get("api_key") or "").strip()
    form_base_url = (data.get("base_url") or "").strip()
    form_model_name = (data.get("model") or "").strip()

    if model_id:
        # 模式 1：从已保存配置加载，再用表单值覆盖（支持未保存时测试）
        cfg = load_config()
        for m in cfg.get("models", []):
            if m.get("id") == model_id:
                target = m.copy()
                break
        if not target:
            return jsonify({"success": False, "message": f"未找到模型：{model_id}"}), 404

        # 用请求中的表单值覆盖（用户刚输入但还没保存的值优先）
        if form_api_key and not form_api_key.startswith("*"):
            target["api_key"] = form_api_key
        if form_base_url:
            target["base_url"] = form_base_url
        if form_model_name:
            target["model"] = form_model_name

        if not target.get("api_key"):
            return jsonify({"success": False, "message": "请先填写 API Key"}), 400
    else:
        # 模式 2：直接使用传入的临时配置
        target = {
            "api_key": form_api_key,
            "base_url": form_base_url,
            "model": form_model_name,
        }
        if not target["api_key"]:
            return jsonify({"success": False, "message": "请输入 API Key"}), 400
        if not target["base_url"]:
            return jsonify({"success": False, "message": "请输入 API Base URL"}), 400
        if not target["model"]:
            return jsonify({"success": False, "message": "请输入模型名称"}), 400

    base_url = target["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {target['api_key']}",
    }

    body = {
        "model": target["model"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 10,
    }

    import time
    import requests

    try:
        t0 = time.time()
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        elapsed = round((time.time() - t0) * 1000)  # ms

        if resp.status_code == 200:
            log_info(f"测试模型连接成功：{target.get('name','') or target['model']} @ {base_url}（{elapsed}ms）")
            return jsonify({
                "success": True,
                "message": f"连接成功（延迟 {elapsed}ms）",
                "latency_ms": elapsed,
            })
        else:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                detail = resp.text[:200]
            log_error(f"测试模型连接失败：{target.get('name','') or target['model']} @ {base_url}，API 返回 {resp.status_code}：{detail or '未知错误'}")
            return jsonify({
                "success": False,
                "message": f"API 返回 {resp.status_code}：{detail or '未知错误'}",
                "latency_ms": elapsed,
            })

    except requests.exceptions.Timeout:
        log_error(f"测试模型连接超时：{target.get('name','') or target.get('model','')} @ {base_url}")
        return jsonify({"success": False, "message": "连接超时（15 秒），请检查 API 地址和网络"})
    except requests.exceptions.ConnectionError:
        log_error(f"测试模型无法连接：{target.get('name','') or target.get('model','')} @ {base_url}")
        return jsonify({"success": False, "message": "无法连接，请检查 API Base URL 是否正确"})
    except Exception as e:
        log_error(f"测试模型失败：{target.get('name','') or target.get('model','')} @ {base_url}，错误：{str(e)[:300]}")
        return jsonify({"success": False, "message": f"测试失败：{str(e)}"})


@settings_bp.route("/api/settings/discover-models", methods=["POST"])
def discover_models():
    """自动查询某个 API 接入点可用的模型列表（调用 OpenAI 兼容的 GET /models 接口）"""
    import requests

    data = request.get_json(silent=True) or {}
    base_url = (data.get("base_url") or "").strip().rstrip("/")
    api_key = (data.get("api_key") or "").strip()

    if not base_url:
        return jsonify({"success": False, "message": "请先填写 API Base URL"}), 400
    if not api_key:
        return jsonify({"success": False, "message": "请先填写 API Key"}), 400

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=15)
    except requests.exceptions.Timeout:
        log_error(f"查询模型列表超时：{base_url}")
        return jsonify({"success": False, "message": "查询超时（15 秒），请检查 API 地址和网络"})
    except requests.exceptions.ConnectionError:
        log_error(f"查询模型列表无法连接：{base_url}")
        return jsonify({"success": False, "message": "无法连接，请检查 API Base URL 是否正确"})
    except Exception as e:
        log_error(f"查询模型列表失败：{base_url}，错误：{str(e)[:300]}")
        return jsonify({"success": False, "message": f"查询失败：{str(e)}"})

    if resp.status_code == 200:
        try:
            payload = resp.json()
        except Exception:
            payload = {}
        # 兼容两种返回结构：{"data":[{"id":...}]} 或 {"object":"list","data":[...]}
        items = payload.get("data", []) if isinstance(payload, dict) else []
        ids = []
        for m in items:
            if isinstance(m, dict) and m.get("id"):
                ids.append(m["id"])
            elif isinstance(m, str) and m:
                ids.append(m)
        ids = sorted(set(ids))
        log_info(f"查询模型列表成功：{base_url}，共 {len(ids)} 个模型")
        return jsonify({"success": True, "models": ids})
    else:
        detail = ""
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except Exception:
            detail = resp.text[:200]
        log_error(f"查询模型列表失败：{base_url}，API 返回 {resp.status_code}：{detail or '未知错误'}")
        return jsonify({
            "success": False,
            "message": f"查询失败（HTTP {resp.status_code}）：{detail or '该接入点不支持 /models 接口'}"
        })


@settings_bp.route("/api/settings/models", methods=["POST"])
def create_model():
    """创建自定义模型"""
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    api_key = data.get("api_key", "") or ""
    base_url = (data.get("base_url") or "").strip()
    model = (data.get("model") or "").strip()
    supports_vision = bool(data.get("supports_vision", False))

    if not name:
        return jsonify({"success": False, "message": "请输入模型名称"}), 400
    if not api_key:
        return jsonify({"success": False, "message": "请输入 API Key"}), 400
    if not base_url:
        return jsonify({"success": False, "message": "请输入 API Base URL"}), 400
    if not model:
        return jsonify({"success": False, "message": "请输入模型名称（模型 ID）"}), 400

    cfg = load_config()

    # 生成唯一 ID
    import uuid
    new_id = "custom_" + uuid.uuid4().hex[:8]
    while any(m.get("id") == new_id for m in cfg.get("models", [])):
        new_id = "custom_" + uuid.uuid4().hex[:8]

    new_model = {
        "id": new_id,
        "name": name,
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "enabled": True,
        "supports_vision": supports_vision,
        "is_custom": True,
    }
    cfg.setdefault("models", []).append(new_model)
    save_config(cfg)

    # 返回不带 api_key 的安全副本
    safe = new_model.copy()
    safe["api_key_masked"] = "*" * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else api_key
    safe["api_key"] = ""
    return jsonify({"success": True, "message": "模型已创建", "model": safe})


@settings_bp.route("/api/settings/models/<model_id>", methods=["DELETE"])
def delete_model(model_id):
    """删除自定义模型"""
    cfg = load_config()
    new_models = [m for m in cfg.get("models", []) if m.get("id") != model_id]
    if len(new_models) == len(cfg.get("models", [])):
        return jsonify({"success": False, "message": "未找到该模型"}), 404

    cfg["models"] = new_models
    if cfg.get("active_model") == model_id:
        cfg["active_model"] = ""
    save_config(cfg)
    return jsonify({"success": True, "message": "模型已删除"})
