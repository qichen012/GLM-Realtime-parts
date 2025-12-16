#!/bin/bash
# 停止 Memobase 自动同步守护进程

cd "$(dirname "$0")/.."

PID_FILE="data/auto_sync.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "🛑 正在停止守护进程 (PID: $PID)..."
    
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ 守护进程已停止"
        rm "$PID_FILE"
    else
        echo "⚠️ 进程不存在 (PID: $PID)"
        rm "$PID_FILE"
    fi
else
    echo "⚠️ 未找到 PID 文件，守护进程可能未运行"
    echo "💡 如需手动停止，使用: ps aux | grep auto_sync_daemon"
fi

