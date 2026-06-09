"""
设置 API — Blueprint
管理多个大模型的 API 配置，包含 4 个内置模型 + 1 个自定义模型
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
            "model": "deepseek-v4-flash",
            "enabled": False,
            "supports_vision": False,  # V4 API 暂不支持多模态
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
            "id": "custom",
            "name": "自定义模型",
            "api_key": "",
            "base_url": "",
            "model": "",
            "enabled": False,
            "supports_vision": False,
        },
    ],
    "active_model": "",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 确保自定义模型始终存在
            if not any(m.get("id") == "custom" for m in cfg.get("models", [])):
                cfg.setdefault("models", []).append(DEFAULT_CONFIG["models"][4])
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
    """测试大模型连接 — 发送简短消息，返回延迟和状态"""
    data = request.get_json(silent=True) or {}
    model_id = data.get("model_id", "")

    if not model_id:
        return jsonify({"success": False, "message": "缺少 model_id"}), 400

    # 临时读取配置中的指定模型（不依赖 active_model）
    cfg = load_config()
    target = None
    for m in cfg.get("models", []):
        if m.get("id") == model_id:
            target = m
            break

    if not target:
        return jsonify({"success": False, "message": f"未找到模型：{model_id}"}), 404

    if not target.get("enabled"):
        return jsonify({"success": False, "message": "请先启用该模型"}), 400

    if not target.get("api_key"):
        return jsonify({"success": False, "message": "请先填写 API Key"}), 400

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
