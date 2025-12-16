# data_logger.py
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

class DialogueLogger:
    """
    一个专门用于记录AI对话的类。
    它负责管理对话状态并将其保存为JSONL格式。
    
    【方案3增强】：
    - 添加同步状态字段 (synced, retry_count)
    - 支持唯一ID追踪
    - 支持时间戳记录
    """
    
    def __init__(self, filename="training_data.jsonl"):
        self.filename = filename
        self.user_text = ""
        self.assistant_text = ""
        
        # 打印日志，确认文件位置
        abs_path = os.path.abspath(filename)
        print(f"\n💾 [Logger] 已初始化。将保存数据到: {abs_path}")

    def log_user_input(self, text: str):
        """
        记录用户的输入（转录文本）。
        这标志着新一轮对话的开始。
        """
        if text:
            self.user_text = text
            # 重置AI回复，为新一轮做准备
            self.assistant_text = ""
            print(f"\n💾 [Logger] 已暂存用户输入: {text[:30]}...")

    def log_assistant_delta(self, delta_text: str):
        """
        累加AI的回复（流式 delta 文本）。
        """
        if delta_text:
            self.assistant_text += delta_text

    def finalize_turn(self) -> Optional[Dict[str, Any]]:
        """
        在AI回复完成后，将完整的一轮对话保存到文件。
        
        【方案3增强】：
        - 添加 synced 状态字段（初始为 false）
        - 添加 retry_count 字段（初始为 0）
        - 添加时间戳
        - 返回对话数据供实时同步使用
        
        Returns:
            dict: 保存的对话数据（包含同步状态），如果失败返回 None
        """
        # 确保我们有完整的一轮对话
        if not self.user_text or not self.assistant_text:
            print(f"\n💾 [Logger] 缺少用户或AI文本，跳过保存。")
            return None

        # 构建标准聊天训练格式 + 同步状态追踪
        data_entry = {
            "messages": [
                {"role": "user", "content": self.user_text},
                {"role": "assistant", "content": self.assistant_text}
            ],
            # 🔑 方案3新增：同步状态追踪
            "synced": False,          # 是否已同步到 Memobase
            "retry_count": 0,         # 重试次数
            "timestamp": datetime.now().isoformat(),  # 时间戳
        }

        try:
            # 使用 'a' (append) 模式追加写入
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(json.dumps(data_entry, ensure_ascii=False) + "\n")
            
            print(f"\n💾 [Logger] 成功保存对话到 {self.filename} (synced=False)")
            
            # 🔑 返回数据供实时同步使用
            return data_entry
            
        except Exception as e:
            print(f"\n❌ [Logger] 保存对话失败: {e}")
            return None
        finally:
            # 保存后清空，准备下一轮
            self.user_text = ""
            self.assistant_text = ""
    
    def update_sync_status(self, line_number: int, synced: bool = True) -> bool:
        """
        更新指定行的同步状态
        
        【方案3核心功能】：
        - 实时同步成功后调用，标记 synced = True
        - 定时任务同步成功后也调用
        
        Args:
            line_number: 行号（从1开始）
            synced: 是否已同步
        
        Returns:
            bool: 更新是否成功
        """
        try:
            # 读取所有行
            if not os.path.exists(self.filename):
                return False
            
            with open(self.filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 检查行号有效性
            if line_number < 1 or line_number > len(lines):
                print(f"⚠️ [Logger] 行号无效: {line_number}")
                return False
            
            # 解析并更新该行
            line_idx = line_number - 1
            try:
                data = json.loads(lines[line_idx].strip())
                data['synced'] = synced
                lines[line_idx] = json.dumps(data, ensure_ascii=False) + "\n"
            except json.JSONDecodeError:
                print(f"⚠️ [Logger] 第 {line_number} 行 JSON 解析失败")
                return False
            
            # 写回文件
            with open(self.filename, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            print(f"✅ [Logger] 更新第 {line_number} 行同步状态: synced={synced}")
            return True
            
        except Exception as e:
            print(f"❌ [Logger] 更新同步状态失败: {e}")
            return False
    
    def get_unsynced_dialogues(self) -> list:
        """
        获取所有未同步的对话
        
        【方案3核心功能】：
        - 供定时任务使用，找出所有 synced=False 的记录
        
        Returns:
            list: [(line_number, dialogue_data), ...]
        """
        unsynced = []
        
        try:
            if not os.path.exists(self.filename):
                return unsynced
            
            with open(self.filename, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        # 检查是否未同步
                        if not data.get('synced', False):
                            unsynced.append((line_no, data))
                    except json.JSONDecodeError:
                        continue
            
            return unsynced
            
        except Exception as e:
            print(f"❌ [Logger] 读取未同步对话失败: {e}")
            return []