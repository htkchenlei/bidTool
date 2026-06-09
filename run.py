#!/usr/bin/env python3
"""
BidTool — 投标工具启动脚本
"""
import subprocess
import sys
import os


def main():
    print("正在检查依赖...")
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-r", req_path, "-q"
    ])

    app_path = os.path.join(os.path.dirname(__file__), "backend", "app.py")
    os.execv(sys.executable, [sys.executable, app_path])


if __name__ == "__main__":
    main()
