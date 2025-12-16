#!/bin/bash
# Memobase 自动同步守护进程启动脚本

cd "$(dirname "$0")/.."

echo "🚀 启动 Memobase 自动同步守护进程..."
echo "💡 日志保存在: data/auto_sync.log"
echo ""

# 如果使用虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 启动守护进程（后台运行）
if [ "$1" = "background" ] || [ "$1" = "bg" ]; then
    echo "📦 后台模式启动..."
    nohup python start_auto_sync.py > data/auto_sync_stdout.log 2>&1 &
    echo $! > data/auto_sync.pid
    echo "✅ 守护进程已在后台启动"
    echo "📝 进程 ID: $(cat data/auto_sync.pid)"
    echo "📂 日志文件: data/auto_sync.log"
    echo ""
    echo "停止守护进程: ./memory/stop_daemon.sh"
    echo "查看日志: tail -f data/auto_sync.log"
else
    echo "🔍 前台模式启动 (按 Ctrl+C 退出)..."
    echo ""
    python start_auto_sync.py
fi

