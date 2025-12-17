#!/usr/bin/env python3
# coding: utf-8
"""
启动 GLM-Realtime 语音助手 (Client VAD 模式)

Client VAD 特点:
- 客户端控制语音检测 (使用本地 WebRTC VAD)
- 自动检测语音结束并提交音频
- 更灵活的控制逻辑
- 可自定义静音阈值

从项目根目录运行:
    python run_clientVAD.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # 导入并运行 Client VAD 主程序
    from app.realtime_client_vad import main
    main()

