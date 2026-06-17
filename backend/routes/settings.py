"""
设置 API — Blueprint
管理多个大模型的 API 配置，包含 5 个内置模型，用户可通过"新建自定义模型"添加任意数量的兼容 OpenAI 格式的模型
"""
import os
import json
from flask import Blueprint, jsonify, request

settings_bp = Blueprint("settings", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "models": [
        {
            "id": "openai",
            "name": "OpenAI GPT",
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o",
            "enabled": False,
            "supports_vision": True,
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "api_key": "",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "enabled": False,
            "supports_vision": False,
        },
        {
            "id": "qwen",
            "name": "阿里通义千问",
            "api_key": "",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-max",
            "enabled": False,
            "supports_vision": False,
        },
        {
            "id": "zhipu",
            "name": "智谱 GLM",
            "api_key": "",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash",
            "enabled": False,
            "supports_vision": False,
        },
        {
            "id": "agnes",
            "name": "Agnes 2.0 Flash",
            "api_key": "",
            "base_url": "https://apihub.agnes-ai.com/v1",
            "model": "agnes-2.0-flash",
            "enabled": False,
            "supports_vision": True,
            "is_free": True,
            "description": "免费模型，支持1M超长上下文，适合长文档分析。注册地址: platform.agnes-ai.com",
        },
    ],
    "active_model": "",
}

# 内置模型 ID，用户不能删除这些
BUILTIN_MODEL_IDS = {"openai", "deepseek", "qwen", "zhipu", "agnes"}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            # 迁移：确保内置模型都存在（新增的内置模型自动补齐）
            existing_ids = {m.get("id") for m in cfg.get("models", [])}
            for default_model in DEFAULT_CONFIG["models"]:
                if default_model["id"] not in existing_ids:
                    cfg.setdefault("models", []).append(default_model)

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
            return jsonify({
                "success": False,
                "message": f"API 返回 {resp.status_code}：{detail or '未知错误'}",
                "latency_ms": elapsed,
            })

    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "连接超时（15 秒），请检查 API 地址和网络"})
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "message": "无法连接，请检查 API Base URL 是否正确"})
    except Exception as e:
        return jsonify({"success": False, "message": f"测试失败：{str(e)}"})


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
    """删除自定义模型（内置模型不可删除）"""
    if model_id in BUILTIN_MODEL_IDS:
        return jsonify({"success": False, "message": "内置模型不可删除"}), 400

    cfg = load_config()
    new_models = [m for m in cfg.get("models", []) if m.get("id") != model_id]
    if len(new_models) == len(cfg.get("models", [])):
        return jsonify({"success": False, "message": "未找到该模型"}), 404

    cfg["models"] = new_models
    if cfg.get("active_model") == model_id:
        cfg["active_model"] = ""
    save_config(cfg)
    return jsonify({"success": True, "message": "模型已删除"})
