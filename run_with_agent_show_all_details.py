#!/usr/bin/env python3
# coding: utf-8
"""
启动集成版 GLM-Realtime 语音助手（Agent + Memory）- 调试版本
所有执行步骤都会记录到 result.txt 文件中
"""

import sys
import os
import time
import json
import queue
import threading
import numpy as np
import sounddevice as sd
import websocket
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 日志文件路径
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result.txt")

class DetailedLogger:
    """详细日志记录器"""
    
    def __init__(self, log_file):
        self.log_file = log_file
        # 清空旧日志
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"GLM-Realtime 详细日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
    
    def log(self, category, message, data=None):
        """记录日志"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] [{category}] {message}\n"
        
        if data:
            if isinstance(data, dict) or isinstance(data, list):
                log_entry += f"  数据: {json.dumps(data, ensure_ascii=False, indent=2)}\n"
            else:
                log_entry += f"  数据: {data}\n"
        
        log_entry += "\n"
        
        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # 也打印到控制台（简化版）
        print(f"[{category}] {message}")

# 创建全局日志记录器
logger = DetailedLogger(LOG_FILE)

# 导入必要的模块
logger.log("INIT", "开始导入模块...")

try:
    from app.realtime import (
        API_KEY, WS_URL, SAMPLE_RATE, 
        session_ready, stop_event, audio_queue,
        generate_jwt_token, tts_worker_thread, keyboard_listener_thread,
        create_sync_worker, audio_played_in_response, voice_processor
    )
    from agents.function_definitions import get_function_definitions
    from agents.claude_code_client import execute_function_call
    from memory.memory_manager import format_memory_for_glm, DEFAULT_USER_ID
    logger.log("INIT", "✅ 所有模块导入成功")
except Exception as e:
    logger.log("ERROR", f"模块导入失败: {e}")
    import traceback
    logger.log("ERROR", "错误堆栈", traceback.format_exc())
    sys.exit(1)

# 全局用户 ID
CURRENT_USER_ID = DEFAULT_USER_ID
logger.log("INIT", f"当前用户ID: {CURRENT_USER_ID}")

# 全局变量用于追踪状态
session_state = {
    "connected": False,
    "session_ready": False,
    "audio_sent_count": 0,
    "speech_started_count": 0,
    "speech_stopped_count": 0,
    "response_received_count": 0,
    "audio_chunks_received": 0,
    "function_calls": []
}


# 增强版消息处理
def on_message_with_agent_debug(ws, message):
    """增强版消息处理：支持 function call + 详细日志"""
    global audio_played_in_response
    
    try:
        data = json.loads(message)
        msg_type = data.get("type")
        
        # 记录所有消息
        logger.log("WS_MESSAGE", f"收到消息类型: {msg_type}")
        
        # 只记录关键消息的完整数据
        if msg_type in ("session.created", "session.updated", "error", "session.error",
                       "response.function_call_arguments.done", "input_audio_buffer.speech_started",
                       "input_audio_buffer.speech_stopped"):
            logger.log("WS_MESSAGE_DETAIL", f"完整消息内容", data)
        
        # 🔧 处理 Function Call
        if msg_type == "response.function_call_arguments.done":
            try:
                function_name = data.get("name", "")
                arguments_str = data.get("arguments", "{}")
                
                logger.log("FUNCTION_CALL", f"收到函数调用: {function_name}", 
                          {"arguments": arguments_str})
                
                session_state["function_calls"].append({
                    "name": function_name,
                    "arguments": arguments_str,
                    "timestamp": time.time()
                })
                
                # 解析参数
                arguments = json.loads(arguments_str)
                
                # 调用 Claude Code Sub Agent
                logger.log("AGENT", f"正在调用 Claude Code Agent...")
                result = execute_function_call(function_name, arguments)
                
                logger.log("AGENT", f"Agent 执行完成", {"result": result})
                
                # 将结果返回给 GLM
                output_message = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "output": json.dumps(result, ensure_ascii=False)
                    }
                }
                
                ws.send(json.dumps(output_message))
                logger.log("WS_SEND", "发送函数调用结果给 GLM")
                
                # 请求 GLM 用这个结果生成回复
                time.sleep(0.1)
                ws.send(json.dumps({"type": "response.create"}))
                logger.log("WS_SEND", "请求 GLM 生成语音回复")
                
            except Exception as e:
                logger.log("ERROR", f"Function Call 处理错误: {e}")
                import traceback
                logger.log("ERROR", "错误堆栈", traceback.format_exc())
        
        # 会话状态
        elif msg_type in ("session.created", "session.updated"):
            session_state["session_ready"] = True
            logger.log("SESSION", f"会话{'建立' if msg_type == 'session.created' else '更新'}")
        
        # 用户输入转写
        elif msg_type == "conversation.item.input_audio_transcription.completed":
            user_text = data.get("transcript", "")
            logger.log("TRANSCRIPTION", f"用户输入转写: {user_text}")
        
        # VAD 检测
        elif msg_type == "input_audio_buffer.speech_started":
            session_state["speech_started_count"] += 1
            logger.log("VAD", f"检测到语音开始 (第 {session_state['speech_started_count']} 次)")
        
        elif msg_type == "input_audio_buffer.speech_stopped":
            session_state["speech_stopped_count"] += 1
            logger.log("VAD", f"检测到语音结束 (第 {session_state['speech_stopped_count']} 次)")
        
        # AI 回复
        elif msg_type == "response.created":
            session_state["response_received_count"] += 1
            logger.log("RESPONSE", f"AI 开始生成回复 (第 {session_state['response_received_count']} 次)")
        
        elif msg_type == "response.audio_transcript.done":
            transcript = data.get("transcript", "")
            logger.log("RESPONSE", f"AI 回复文字: {transcript}")
        
        elif msg_type == "response.audio.delta":
            session_state["audio_chunks_received"] += 1
            audio_base64 = data.get("delta", "")
            if audio_base64:
                logger.log("AUDIO", f"收到音频块 #{session_state['audio_chunks_received']}, 大小: {len(audio_base64)} bytes (base64)")
        
        elif msg_type == "response.audio.done":
            logger.log("AUDIO", f"音频接收完成，总共 {session_state['audio_chunks_received']} 块")
            logger.log("AUDIO_PLAY", "准备调用播放逻辑...")
            session_state["audio_chunks_received"] = 0  # 重置计数
        
        elif msg_type == "response.done":
            logger.log("RESPONSE", "AI 回复完成")
            logger.log("STATE", "当前状态统计", session_state)
        
        # 错误处理
        elif msg_type in ("error", "session.error"):
            error_info = data.get('error', {})
            logger.log("ERROR", f"API 错误: {error_info.get('message', data)}", error_info)
        
        # 调用原始的 on_message 函数处理实际逻辑
        from app.realtime import on_message as original_on_message
        try:
            original_on_message(ws, message)
            
            # 播放完成后记录
            if msg_type == "response.audio.done":
                logger.log("AUDIO_PLAY", "音频播放处理完成")
        except Exception as e:
            logger.log("ERROR", f"原始消息处理出错: {e}")
            import traceback
            logger.log("ERROR", "错误堆栈", traceback.format_exc())
        
    except Exception as e:
        logger.log("ERROR", f"消息处理异常: {e}")
        import traceback
        logger.log("ERROR", "错误堆栈", traceback.format_exc())


# 增强版连接建立
def callback_debug(indata, frames, time_info, status):
    """带日志的麦克风回调函数 - 完全不使用本地 VAD"""
    from app.realtime import stop_event, audio_queue
    import numpy as np
    
    if status:
        logger.log("MIC", f"麦克风警告: {status}")
    
    if stop_event.is_set():
        return
    
    volume_norm = np.linalg.norm(indata) * 10
    
    # 记录音量和队列状态
    if volume_norm > 100000:
        logger.log("MIC", f"检测到高音量: {volume_norm:.0f}, 队列大小: {audio_queue.qsize()}")
    elif volume_norm > 10000 and session_state.get("last_volume_log", 0) + 2 < time.time():
        logger.log("MIC", f"检测到中等音量: {volume_norm:.0f}, 队列大小: {audio_queue.qsize()}")
        session_state["last_volume_log"] = time.time()
    
    # 🔑 关键修改：不使用本地 VAD，直接发送所有音频到队列
    # 让 Server VAD 来决定什么是语音
    audio_queue.put(indata.copy())
    
    # 记录队列状态
    if session_state.get("last_queue_log", 0) + 5 < time.time():
        logger.log("AUDIO_QUEUE", f"队列大小: {audio_queue.qsize()}")
        session_state["last_queue_log"] = time.time()


# 🔑 新增：手动触发机制
manual_trigger_flag = threading.Event()

def manual_trigger_listener():
    """监听空格键，手动触发 Server VAD 停止"""
    from pynput import keyboard as kb
    
    def on_press(key):
        try:
            if key == kb.Key.space:
                print("\n🔔 [空格键] 手动触发语音结束...")
                logger.log("MANUAL", "用户按下空格键，准备手动触发语音结束")
                manual_trigger_flag.set()
        except AttributeError:
            pass
    
    with kb.Listener(on_press=on_press) as listener:
        listener.join()


def send_audio_loop_debug(ws):
    """带日志的音频发送循环 + 手动触发支持"""
    from app.realtime import session_ready, stop_event, audio_queue, SAMPLE_RATE, pcm_to_wav_base64
    import numpy as np
    
    session_ready.wait()
    logger.log("AUDIO_LOOP", "会话就绪，开始发送音频流")
    
    MAX_QPS = 20
    MIN_INTERVAL = 1.0 / MAX_QPS
    BATCH_SIZE = 16
    
    audio_batch = []
    last_send_time = 0
    total_chunks_sent = 0
    last_manual_trigger_time = 0
    
    logger.log("AUDIO_LOOP", f"配置: MAX_QPS={MAX_QPS}, BATCH_SIZE={BATCH_SIZE}")
    
    while not stop_event.is_set():
        # 🔑 首先检查手动触发（在循环开始就检查，不管队列状态）
        if manual_trigger_flag.is_set() and (time.time() - last_manual_trigger_time) > 1:
            logger.log("MANUAL", "手动触发：清空音频缓冲并请求响应")
            manual_trigger_flag.clear()
            last_manual_trigger_time = time.time()
            
            try:
                # 提交当前音频缓冲
                ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                logger.log("WS_SEND", "手动提交音频缓冲")
                time.sleep(0.1)
                
                # 创建响应
                ws.send(json.dumps({"type": "response.create"}))
                logger.log("WS_SEND", "手动创建响应请求")
                
                print("   ✅ 已手动触发，等待 AI 回复...")
            except Exception as e:
                logger.log("ERROR", f"手动触发失败: {e}")
        
        try:
            chunk = audio_queue.get(timeout=0.05)
            audio_batch.append(chunk)
            
            if len(audio_batch) >= BATCH_SIZE:
                time_since_last_send = time.time() - last_send_time
                if time_since_last_send < MIN_INTERVAL:
                    time.sleep(MIN_INTERVAL - time_since_last_send)
                
                combined_audio = np.concatenate(audio_batch)
                audio_base64 = pcm_to_wav_base64(combined_audio, SAMPLE_RATE)
                
                ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }))
                
                total_chunks_sent += 1
                last_send_time = time.time()
                
                if total_chunks_sent % 10 == 0:  # 每10批记录一次
                    logger.log("AUDIO_SEND", f"已发送 {total_chunks_sent} 批音频数据")
                
                audio_batch.clear()
                
                for _ in range(BATCH_SIZE):
                    try:
                        audio_queue.task_done()
                    except:
                        pass

        except queue.Empty:
            continue
        except Exception as e:
            logger.log("ERROR", f"音频发送错误: {e}")
            break
    
    logger.log("AUDIO_LOOP", f"音频发送线程退出，总共发送 {total_chunks_sent} 批")


def on_open_with_agent_debug(ws):
    """增强版连接建立：配置 function call + 用户记忆 + 详细日志"""
    session_state["connected"] = True
    logger.log("CONNECTION", "WebSocket 连接已建立")
    
    # 🧠 获取用户记忆
    logger.log("MEMORY", "正在加载用户记忆...")
    try:
        memory_context = format_memory_for_glm(CURRENT_USER_ID)
        if memory_context:
            logger.log("MEMORY", "✅ 用户记忆已加载", {"context_length": len(memory_context)})
        else:
            logger.log("MEMORY", "⚠️ 未获取到用户记忆")
    except Exception as e:
        logger.log("ERROR", f"记忆加载失败: {e}")
        memory_context = None
    
    # 获取 function 定义
    logger.log("TOOLS", "正在加载 function 定义...")
    try:
        tools = get_function_definitions()
        logger.log("TOOLS", f"✅ 加载了 {len(tools)} 个工具", 
                  {"tools": [t["name"] for t in tools]})
    except Exception as e:
        logger.log("ERROR", f"工具加载失败: {e}")
        tools = []
    
    # 构建系统指令
    system_instructions = """你是一个智能旅行助手，能帮用户规划行程、订票、订酒店。

请根据用户的历史记忆提供个性化、贴心的服务。
如果用户的记忆中有相关信息（如偏好、习惯、历史计划等），请自然地运用这些信息。
不要刻意提及"我看到你的记忆"，而是自然地体现在服务中。"""
    
    if memory_context:
        system_instructions += f"\n\n{memory_context}"
    
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,              # 降低阈值，更容易检测到语音
                "silence_duration_ms": 700,    # 🔑 降低到 0.7 秒，更容易触发停止
                "prefix_padding_ms": 300
            },
            "input_audio_transcription": {"enabled": True},
            "temperature": 0.8,
            "modalities": ["audio", "text"],
            "voice": "female-sweet",
            "tools": tools,
            "instructions": system_instructions,
            "beta_fields": {
               "chat_mode": "audio",
               "tts_source": "e2e",
               "auto_search": False,
               "voice": "female-sweet"
           }
        }
    }
    
    logger.log("CONFIG", "会话配置", {
        "tools_count": len(tools),
        "has_memory": bool(memory_context),
        "vad_threshold": 0.5,
        "silence_duration": 700,
        "voice": "female-sweet"
    })
    
    logger.log("WS_SEND", "发送会话配置...")
    ws.send(json.dumps(session_config))
    
    time.sleep(0.5)
    
    # 启动带日志的音频发送线程
    logger.log("THREAD", "启动带日志的音频发送线程...")
    threading.Thread(target=send_audio_loop_debug, args=(ws,), daemon=True).start()


def on_close_debug(ws, close_status_code, close_msg):
    """连接关闭 - 带日志"""
    logger.log("CONNECTION", f"连接已关闭: code={close_status_code}, msg={close_msg}")


def on_error_debug(ws, error):
    """错误处理 - 带日志"""
    logger.log("ERROR", f"WebSocket 错误: {error}")


# --- Main Program ---
if __name__ == "__main__":
    logger.log("MAIN", "程序启动")
    
    if not API_KEY:
        logger.log("ERROR", "未设置 ZHIPU_API_KEY 环境变量")
        print("❌ Please set the ZHIPU_API_KEY environment variable first")
        sys.exit(1)
    
    logger.log("MAIN", "✅ API Key 已配置")

    # 音频设备检查
    logger.log("AUDIO", "检查音频设备...")
    print("\n" + "="*60)
    print("🔊 Audio Device Check")
    print("="*60)
    try:
        input_device = sd.query_devices(kind='input')['name']
        output_device = sd.query_devices(kind='output')['name']
        logger.log("AUDIO", f"输入设备: {input_device}")
        logger.log("AUDIO", f"输出设备: {output_device}")
        print(f"Default input device: {input_device}")
        print(f"Default output device: {output_device}")
        
        print("\n🧪 Testing audio playback...")
        test_tone = (np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE) * 5000).astype(np.int16)
        sd.play(test_tone, samplerate=SAMPLE_RATE, blocking=True)
        print("✅ If you heard a beep, audio output is working!")
        logger.log("AUDIO", "✅ 音频测试完成")
        time.sleep(0.5)
    except Exception as e:
        logger.log("ERROR", f"音频设备检查失败: {e}")
        print(f"⚠️  Audio device warning: {e}")
    print("="*60 + "\n")

    # 初始化实时同步工作器
    logger.log("SYNC", "初始化 Memobase 实时同步...")
    try:
        sync_worker = create_sync_worker(CURRENT_USER_ID)
        logger.log("SYNC", "✅ 实时同步工作器已启动")
        print("✅ 实时同步工作器已启动")
    except Exception as e:
        logger.log("SYNC", f"⚠️ 实时同步工作器初始化失败: {e}")
        print(f"⚠️  实时同步工作器初始化失败: {e}")
        sync_worker = None

    # 生成 JWT Token
    logger.log("AUTH", "生成 JWT Token...")
    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
        logger.log("AUTH", "✅ JWT Token 生成成功")
        print("✅ JWT generated successfully")
    except Exception as e:
        logger.log("ERROR", f"JWT Token 生成失败: {e}")
        print(f"❌ JWT generation failed: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("    GLM-Realtime + Claude Code Travel Assistant")
    print("    (调试版本 - 日志记录到 result.txt)")
    print("="*60)
    print("🤖 功能:")
    print("   • 语音对话 + 实时记忆同步")
    print("   • 行程规划（调用 Claude Code Agent）")
    print("   • 订票服务（调用 Claude Code Agent + Skill）")
    print("   • 订酒店（调用 Claude Code Agent + Skill）")
    print("\n⌨️  控制键:")
    print("   • 空格键 (Space) = 手动表示「我说完了」")
    print("   • 回车键 (Enter) = 打断 AI 回复")
    print("   • Ctrl+C = 退出程序")
    print("\n💡 使用示例:")
    print("   1. 说话：「帮我规划一个去北京的旅行」")
    print("   2. 按空格键表示说完")
    print("   3. 等待 AI 回复")
    print(f"\n📝 日志文件: {LOG_FILE}")
    print("="*60 + "\n")
    
    logger.log("MAIN", "启动辅助线程...")
    
    # 启动 TTS 线程
    threading.Thread(target=tts_worker_thread, daemon=True).start()
    logger.log("THREAD", "TTS 工作线程已启动")
    
    # 启动键盘监听线程（打断功能）
    threading.Thread(target=keyboard_listener_thread, daemon=True).start()
    logger.log("THREAD", "键盘监听线程已启动（Enter=打断）")
    
    # 🔑 启动手动触发监听线程
    threading.Thread(target=manual_trigger_listener, daemon=True).start()
    logger.log("THREAD", "手动触发监听线程已启动（Space=完成说话）")

    websocket.enableTrace(False)
    
    logger.log("WS", "创建 WebSocket 连接...")
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {AUTH_TOKEN}"],
        on_message=on_message_with_agent_debug,
        on_open=on_open_with_agent_debug,
        on_close=on_close_debug,
        on_error=on_error_debug
    )
    
    # 设置全局 WebSocket 对象（用于打断功能）
    import app.realtime as rt
    rt.ws_global = ws
    logger.log("WS", "全局 WebSocket 对象已设置")
    
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()
    logger.log("THREAD", "WebSocket 线程已启动")

    try:
        print("⏳ Waiting for connection...")
        logger.log("MAIN", "等待连接建立...")
        session_ready.wait(timeout=10)

        if not session_ready.is_set():
            logger.log("ERROR", "会话建立超时")
            print("❌ Session setup timeout")
            sys.exit(1)

        logger.log("MAIN", "✅ 会话已就绪，开始录音")
        print("🎤 Ready! Start speaking...\n")
        
        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype='int16', callback=callback_debug):
            logger.log("AUDIO", "音频输入流已启动（使用调试版callback）")
            ws_thread.join()

    except KeyboardInterrupt:
        logger.log("MAIN", "用户中断程序")
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        logger.log("ERROR", f"运行时错误: {e}")
        print(f"\n❌ Runtime error: {e}")
        import traceback
        logger.log("ERROR", "错误堆栈", traceback.format_exc())
    finally:
        logger.log("MAIN", "开始清理资源...")
        print("\n🛑 正在清理资源...")
        stop_event.set()
        
        if sync_worker:
            logger.log("SYNC", "停止同步工作器...")
            print("⏳ 等待同步队列清空...")
            sync_worker.stop(timeout=5)
        
        if ws:
            logger.log("WS", "关闭 WebSocket 连接...")
            threading.Thread(target=ws.close).start()
        
        sd.stop()
        logger.log("MAIN", "程序退出")
        print("✅ 已退出")
        print(f"\n📝 详细日志已保存到: {LOG_FILE}")

