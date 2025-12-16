#!/bin/bash
# 检查 Memobase 自动同步守护进程状态

cd "$(dirname "$0")/.."

PID_FILE="data/auto_sync.pid"
LOG_FILE="data/auto_sync.log"

echo "🔍 检查守护进程状态..."
echo ""

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    if kill -0 $PID 2>/dev/null; then
        echo "✅ 守护进程运行中"
        echo "📝 进程 ID: $PID"
        
        # 显示进程信息
        echo ""
        echo "进程信息:"
        ps -p $PID -o pid,ppid,etime,cmd
        
        # 显示最近的日志
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "最近的日志 (最后10行):"
            echo "─────────────────────────────────────"
            tail -n 10 "$LOG_FILE"
        fi
    else
        echo "❌ 守护进程未运行 (PID 文件存在但进程不存在)"
        rm "$PID_FILE"
    fi
else
    echo "❌ 守护进程未运行 (未找到 PID 文件)"
fi

echo ""
echo "💡 命令:"
echo "  启动: ./memory/start_daemon.sh"
echo "  停止: ./memory/stop_daemon.sh"
echo "  日志: tail -f $LOG_FILE"

