"""
GLM-Realtime + Claude Code Sub Agent 集成版本
支持通过语音对话调用旅行助手功能
集成 Memobase 用户记忆功能
"""

import json
import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.realtime import *  # 导入原有的所有功能
from agents.function_definitions import get_function_definitions
from agents.claude_code_client import execute_function_call
from memory.memory_manager import format_memory_for_glm, DEFAULT_USER_ID

# 全局用户 ID（可以根据实际情况修改）
CURRENT_USER_ID = DEFAULT_USER_ID


# 覆盖 on_message 函数，添加 function call 处理
def on_message_with_agent(ws, message):
    """增强版消息处理：支持 function call"""
    global audio_played_in_response
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 🔧 处理 Function Call
    if msg_type == "response.function_call_arguments.done":
        try:
            function_name = data.get("name", "")
            arguments_str = data.get("arguments", "{}")
            
            print(f"\n🔔 收到 Function Call: {function_name}")
            print(f"   参数: {arguments_str}")
            
            # 解析参数
            arguments = json.loads(arguments_str)
            
            # 调用 Claude Code Sub Agent
            print(f"\n🤖 正在调用 Claude Code Agent...")
            result = execute_function_call(function_name, arguments)
            
            # 格式化结果
            print(f"   ✅ 执行完成")
            print(f"   结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 将结果返回给 GLM
            output_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "output": json.dumps(result, ensure_ascii=False)
                }
            }
            
            ws.send(json.dumps(output_message))
            print("   📤 结果已发送回 GLM")
            
            # 请求 GLM 用这个结果生成回复
            time.sleep(0.1)
            ws.send(json.dumps({"type": "response.create"}))
            print("   📤 请求 GLM 生成语音回复\n")
            
        except Exception as e:
            print(f"\n❌ Function Call 处理错误: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        # 其他消息类型使用原有的处理逻辑
        # 调用原始的 on_message 函数
        import app.realtime as rt
        rt.on_message(ws, message)


# 覆盖 on_open 函数，添加 tools 配置 + 用户记忆
def on_open_with_agent(ws):
    """增强版连接建立：配置 function call + 用户记忆"""
    print("🔌 WebSocket connected, configuring session with Agent support...")
    
    # 🧠 获取用户记忆
    print("🧠 正在加载用户记忆...")
    memory_context = format_memory_for_glm(CURRENT_USER_ID)
    if memory_context:
        print("   ✅ 用户记忆已加载")
    else:
        print("   ⚠️ 未获取到用户记忆（将继续运行）")
    
    # 获取 function 定义
    tools = get_function_definitions()
    
    # 构建系统指令（包含记忆）
    system_instructions = """你是一个智能旅行助手，能帮用户规划行程、订票、订酒店。

请根据用户的历史记忆提供个性化、贴心的服务。
如果用户的记忆中有相关信息（如偏好、习惯、历史计划等），请自然地运用这些信息。
不要刻意提及"我看到你的记忆"，而是自然地体现在服务中。"""
    
    # 如果有记忆，添加到系统指令中
    if memory_context:
        system_instructions += f"\n\n{memory_context}"
    
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,              # 🔑 降低阈值，更容易检测到语音
                "prefix_padding_ms": 300,      # 说话前缓冲 (毫秒)
                "silence_duration_ms": 700     # 🔑 0.7秒静音即可触发，更灵敏
            },
            "input_audio_transcription": {
                "enabled": True
            },
            "temperature": 0.8,
            "modalities": ["audio", "text"],
            "voice": "female-sweet",  # 🔑 甜美女声
            "tools": tools,  # 🔑 添加 function call 定义
            "instructions": system_instructions,  # 🔑 添加系统指令（包含记忆）
            "beta_fields": {
               "chat_mode": "audio",
               "tts_source": "e2e",
               "auto_search": False,
               "voice": "female-sweet"  # 🔑 甜美女声
           }
        }
    }
    
    print(f"📤 Session config:")
    print(f"   - Tools: {len(tools)} 个")
    for tool in tools:
        print(f"     • {tool['name']}: {tool['description'][:50]}...")
    print(f"   - 用户记忆: {'已加载' if memory_context else '未加载'}")
    
    ws.send(json.dumps(session_config))
    time.sleep(0.5)
    threading.Thread(target=send_audio_loop, args=(ws,), daemon=True).start()


# --- Main Program ---
if __name__ == "__main__":
    if not API_KEY:
        print("❌ Please set the ZHIPU_API_KEY environment variable first")
        sys.exit(1)

    # 音频设备检查
    print("\n" + "="*60)
    print("🔊 Audio Device Check")
    print("="*60)
    try:
        print(f"Default input device: {sd.query_devices(kind='input')['name']}")
        print(f"Default output device: {sd.query_devices(kind='output')['name']}")
        
        print("\n🧪 Testing audio playback...")
        test_tone = (np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE) * 5000).astype(np.int16)
        sd.play(test_tone, samplerate=SAMPLE_RATE, blocking=True)
        print("✅ If you heard a beep, audio output is working!")
        time.sleep(0.5)
    except Exception as e:
        print(f"⚠️  Audio device warning: {e}")
    print("="*60 + "\n")

    # 🔑 方案3：初始化实时同步工作器
    print("🔧 初始化 Memobase 实时同步...")
    try:
        sync_worker = create_sync_worker(CURRENT_USER_ID)
        print("✅ 实时同步工作器已启动")
    except Exception as e:
        print(f"⚠️  实时同步工作器初始化失败: {e}")
        print("💡 将使用定时任务作为后备同步方式")
        sync_worker = None

    # 生成 JWT Token
    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
        print("✅ JWT generated successfully")
    except Exception as e:
        print(f"❌ JWT generation failed: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("    GLM-Realtime + Claude Code Travel Assistant")
    print("="*60)
    print("🤖 功能:")
    print("   • 语音对话 + 实时记忆同步")
    print("   • 行程规划（调用 Claude Code Agent）")
    print("   • 订票服务（调用 Claude Code Agent + Skill）")
    print("   • 订酒店（调用 Claude Code Agent + Skill）")
    print("\n⌨️  快捷键:")
    print("   • 空格键 = 完成说话，立即请求 AI 回复")
    print("   • Enter键 = 打断 AI 回复")
    print("\n💡 使用示例:")
    print("   「帮我规划一个去北京的旅行」")
    print("   「我要订一张明天去上海的火车票」")
    print("   「帮我订一个杭州的酒店」")
    print("="*60 + "\n")
    
    # 启动 TTS 线程
    threading.Thread(target=tts_worker_thread, daemon=True).start()
    
    # 🔑 启动键盘监听线程（用于打断功能）
    threading.Thread(target=keyboard_listener_thread, daemon=True).start()
    
    # 🔑 启动手动触发监听线程（空格键完成说话）
    threading.Thread(target=manual_trigger_listener_thread, daemon=True).start()

    websocket.enableTrace(False)
    
    # 🔑 使用增强版的回调函数
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {AUTH_TOKEN}"],
        on_message=on_message_with_agent,  # 使用增强版
        on_open=on_open_with_agent,        # 使用增强版
        on_close=on_close,
        on_error=on_error
    )
    
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()

    try:
        print("⏳ Waiting for connection...")
        session_ready.wait(timeout=10)

        if not session_ready.is_set():
            print("❌ Session setup timeout")
            sys.exit(1)

        print("🎤 Ready! Start speaking...\n")
        
        # 🔑 创建音频输入流并保存全局引用（用于播放时暂停）
        # 在主程序中，通过 globals() 修改全局变量
        input_stream = sd.InputStream(
            channels=1, 
            samplerate=SAMPLE_RATE, 
            dtype='int16', 
            callback=callback
        )
        globals()['audio_input_stream'] = input_stream
        input_stream.start()
        
        try:
            ws_thread.join()
        finally:
            if input_stream:
                input_stream.stop()
                input_stream.close()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Runtime error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🛑 正在清理资源...")
        stop_event.set()
        
        # 🔑 方案3：停止同步工作器
        if sync_worker:
            print("⏳ 等待同步队列清空...")
            sync_worker.stop(timeout=5)
        
        if ws:
             threading.Thread(target=ws.close).start()
        sd.stop()
        print("✅ 已退出")

