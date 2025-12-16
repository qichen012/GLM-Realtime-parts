#!/usr/bin/env python3
# coding: utf-8
"""
启动集成版 GLM-Realtime 语音助手（Agent + Memory）
从项目根目录运行
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接执行 realtime_with_agent.py
if __name__ == "__main__":
    exec(open("app/realtime_with_agent.py").read())

