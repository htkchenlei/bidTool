"""
LLM API 客户端 — 读取配置中的激活模型，封装 OpenAI 兼容的 /chat/completions 调用
支持文本对话和图片（base64）视觉输入
对文本模型自动尝试 OCR 提取文字后再识别
"""
import os
import json
import base64
import re
import requests
import tempfile
from io import BytesIO

# ── 路径 ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# ── 模型视觉能力检测 ─────────────────────────────────────
# 新方式：从 config.json 的 supports_vision 字段读取
# 旧方式（兜底）：检查模型名称关键词
VISION_MODEL_PREFIXES = ("gpt-4", "gpt-4o", "claude", "gemini", "qvq", "qwen-vl", "glm-4v")
VISION_MODEL_KEYWORDS = ("vision", "vl", "omni", "multimodal")


def _load_config():
    """读取配置，返回 (models_dict, active_model_id)"""
    if not os.path.exists(CONFIG_FILE):
        return None, ""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    models = {m["id"]: m for m in cfg.get("models", [])}
    active = cfg.get("active_model", "")
    return models, active


def get_active_model_config():
    """获取当前激活的大模型配置，如果未设置则返回 None"""
    models, active_id = _load_config()
    if not active_id or active_id not in models:
        return None
    m = models[active_id]
    if not m.get("enabled") or not m.get("api_key"):
        return None
    return m


def _model_supports_vision(cfg: dict) -> bool:
    """检测模型是否支持视觉/多模态输入（优先读取配置中的 supports_vision 字段）"""
    # 优先：从配置字段读取
    if "supports_vision" in cfg:
        return bool(cfg["supports_vision"])
    # 兜底：根据模型名称关键词推断
    model = cfg.get("model", "").lower()
    for prefix in VISION_MODEL_PREFIXES:
        if model.startswith(prefix):
            return True
    for kw in VISION_MODEL_KEYWORDS:
        if kw in model:
            return True
    return False


def _ocr_image_to_text(image_data: bytes) -> str:
    """
    尝试用多种方式从图片中提取文字
    优先使用 pytesseract，否则使用简单的图片信息描述降级方案
    """
    # 方案 1: pytesseract
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(BytesIO(image_data))
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        if text.strip():
            return text.strip()
    except ImportError:
        pass
    except Exception:
        pass

    # 方案 2: 都没有就返回空
    return ""


def encode_image_to_base64(image_data: bytes) -> str:
    """将图片二进制数据转为 base64 data URL"""
    b64 = base64.b64encode(image_data).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def call_llm(messages: list, temperature: float = 0.1, max_tokens: int = 1000) -> str:
    """
    通用 LLM 调用
    :param messages: OpenAI 格式的 messages 列表
    :param temperature: 温度参数（越低越稳定）
    :param max_tokens: 最大输出 token 数
    :return: 模型回复文本
    """
    cfg = get_active_model_config()
    if not cfg:
        raise RuntimeError("未配置或启用大模型，请先在设置中配置并启用一个模型，然后设为默认")

    base_url = cfg["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }

    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)

    if resp.status_code == 400:
        detail = ""
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except Exception:
            detail = resp.text[:300]
        raise RuntimeError(
            f"大模型 API 请求失败 (400)：{detail or '请求参数不合法'}\n"
            "常见原因：\n"
            "1. 模型名称不正确（如 deepseek 应为 deepseek-chat）\n"
            "2. 模型不支持图片/视觉输入（请切换到多模态模型）\n"
            f"3. API Key 无效或过期\n"
            f"当前模型：{cfg['name']} ({cfg.get('model','')})，请检查设置中的模型配置"
        )

    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def extract_cert_from_image(image_data: bytes) -> dict:
    """
    从证书图片中提取资质信息
    - 视觉模型：直接发送 base64 图片
    - 文本模型：先尝试 OCR 提取文字，再文本识别
    """
    cfg = get_active_model_config()
    if not cfg:
        raise RuntimeError("未配置或启用大模型，请先在设置中配置并启用一个模型，然后设为默认")

    model_name = cfg["model"]
    supports_vision = _model_supports_vision(cfg)

    system_prompt = """你是一个专业的资质证书信息提取助手。请从证书内容中提取以下信息，以严格的 JSON 格式返回：

{
  "name": "证书全称",
  "type": "证书类型（如：施工资质、管理体系、安全许可、人员资质、检测认证 等）",
  "issuer": "颁发机构全称",
  "expire": "到期日期，格式为 YYYY-MM-DD，如果未明确标注则填 '' "
}

注意：
1. 只返回 JSON，不要包含任何其他文本或解释。
2. 如果某项信息无法识别，对应的值填空字符串 ''。
3. 日期统一转换为 YYYY-MM-DD 格式。"""

    if supports_vision:
        # ── 视觉模型：直接发送图片 ──
        image_url = encode_image_to_base64(image_data)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请提取这张证书图片中的资质信息"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ]
    else:
        # ── 文本模型：先 OCR 提取文字 ──
        image_text = _ocr_image_to_text(image_data)
        if not image_text:
            raise RuntimeError(
                f"当前激活的模型「{cfg['name']} ({model_name})」不支持图片视觉识别，"
                "且系统未安装 OCR 引擎，无法自动提取图片文字。\n\n"
                "请选择以下方案之一：\n"
                "1. 在设置中切换到支持视觉的大模型（如 GPT-4o 或 Qwen-VL）\n"
                "2. 安装 Tesseract OCR 以便自动提取图片文字：\n"
                "   下载安装：https://github.com/UB-Mannheim/tesseract/wiki\n"
                "   然后运行：pip install pytesseract\n"
                "3. 将证书拍照后转为 PDF 再上传（系统会自动提取 PDF 中的文字）"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请从以下 OCR 提取的证书内容中识别资质信息（注意：OCR 可能有识别错误，请根据上下文修正）：\n\n{image_text[:6000]}"},
        ]

    response = call_llm(messages, temperature=0.0, max_tokens=500)
    return _parse_json_response(response)


def extract_cert_from_text(text: str) -> dict:
    """
    从证书文本中提取资质信息（使用文本模型，适用于 PDF）
    :param text: PDF 提取的文本内容
    :return: {"name": "", "type": "", "issuer": "", "expire": ""}
    """
    system_prompt = """你是一个专业的资质证书信息提取助手。请从以下文档文本中提取证书相关信息，以严格的 JSON 格式返回：

{
  "name": "证书全称",
  "type": "证书类型（如：施工资质、管理体系、安全许可、人员资质、检测认证 等）",
  "issuer": "颁发机构全称",
  "expire": "到期日期，格式为 YYYY-MM-DD，如果未明确标注则填 '' "
}

注意：
1. 只返回 JSON，不要包含任何其他文本或解释。
2. 如果某项信息无法识别，对应的值填空字符串 ''。
3. 日期统一转换为 YYYY-MM-DD 格式。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请从以下文档内容中提取资质证书信息：\n\n{text[:6000]}"},
    ]

    response = call_llm(messages, temperature=0.0, max_tokens=500)
    return _parse_json_response(response)


def _parse_json_response(response: str) -> dict:
    """从 LLM 返回中解析 JSON"""
    default = {"name": "", "type": "", "issuer": "", "expire": ""}
    # 尝试提取 JSON 块
    text = response.strip()
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    try:
        data = json.loads(text)
        result = {}
        for k in default:
            result[k] = str(data.get(k, "")).strip()
        return result
    except json.JSONDecodeError:
        # 尝试更宽松的解析
        import re
        result = default.copy()
        patterns = {
            "name": r'"name"\s*:\s*"([^"]*)"',
            "type": r'"type"\s*:\s*"([^"]*)"',
            "issuer": r'"issuer"\s*:\s*"([^"]*)"',
            "expire": r'"expire"\s*:\s*"([^"]*)"',
        }
        for key, pat in patterns.items():
            m = re.search(pat, response)
            if m:
                result[key] = m.group(1)
        return result
