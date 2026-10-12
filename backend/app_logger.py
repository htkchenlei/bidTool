"""
统一日志模块

- 同时输出到控制台（docker logs 可见）和 data/logs/bidtool.log（随 ./data 卷持久化）
- 提供 API Key 脱敏能力，避免敏感信息落盘
"""
import logging
import os
import re
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "bidtool.log")

_logger = None

# 常见 API Key 形态，用于兜底脱敏（即使配置里没读到也能挡一层）
_KEY_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{4})[A-Za-z0-9_\-]+"),
    re.compile(r"(Bearer\s+[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+"),
]


def get_logger(name="bidtool"):
    global _logger
    if _logger is None:
        os.makedirs(LOG_DIR, exist_ok=True)
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.INFO)
        if not _logger.handlers:
            fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # 文件输出（滚动，单文件最大 5MB，保留 3 份）
            fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt)
            _logger.addHandler(fh)

            # 控制台输出（docker logs / 本地终端可见）
            ch = logging.StreamHandler()
            ch.setFormatter(fmt)
            _logger.addHandler(ch)

    return _logger


def mask_secrets(text):
    """对日志文本做敏感信息脱敏（API Key）"""
    if not text:
        return text
    s = str(text)

    # 1) 从 config.json 读取所有已配置的 api_key 并整体替换
    try:
        config_path = os.path.join(DATA_DIR, "config.json")
        if os.path.exists(config_path):
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for m in cfg.get("models", []):
                key = m.get("api_key") or ""
                if len(key) > 8:
                    s = s.replace(key, key[:6] + "***")
    except Exception:
        pass

    # 2) 正则兜底：sk- 开头、Bearer 后跟的长串
    for pat in _KEY_PATTERNS:
        s = pat.sub(r"\1***", s)

    return s


def log_info(msg):
    get_logger().info(mask_secrets(msg))


def log_warning(msg):
    get_logger().warning(mask_secrets(msg))


def log_error(msg):
    get_logger().error(mask_secrets(msg))
