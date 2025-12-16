"""
分析 WebSocket 消息日志，查找音频数据
"""
import json
import sys
from collections import defaultdict

def analyze_log(log_file):
    print(f"\n{'='*70}")
    print(f"📊 Analyzing: {log_file}")
    print(f"{'='*70}\n")
    
    messages = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            messages.append(json.loads(line))
    
    print(f"✅ Loaded {len(messages)} messages\n")
    
    # 统计消息类型
    print("📈 Message Type Distribution:")
    print("-" * 70)
    type_counts = defaultdict(lambda: {"send": 0, "receive": 0})
    for msg in messages:
        type_counts[msg['type']][msg['direction']] += 1
    
    for msg_type in sorted(type_counts.keys()):
        counts = type_counts[msg_type]
        print(f"  {msg_type:45s} | Sent: {counts['send']:3d} | Received: {counts['receive']:3d}")
    
    # 查找包含音频的消息
    print(f"\n{'='*70}")
    print("🎵 Messages with Audio Data:")
    print("-" * 70)
    
    audio_messages = []
    for msg in messages:
        data = msg['data']
        
        # 检查顶层 audio 字段
        if data.get('_audio_present'):
            audio_messages.append(msg)
            print(f"\n[{msg['sequence']:03d}] {msg['type']} ({msg['direction']})")
            print(f"  ├─ Timestamp: {msg['timestamp']}")
            print(f"  ├─ Audio length: {data.get('_audio_length', 0)} chars")
            
            # 打印其他有用字段
            if 'transcript' in data:
                print(f"  └─ Transcript: {data['transcript'][:100]}")
        
        # 检查嵌套的 item.content 中的 audio
        if 'item' in data and 'content' in data['item']:
            for i, content in enumerate(data['item']['content']):
                if content.get('_audio_present'):
                    audio_messages.append(msg)
                    print(f"\n[{msg['sequence']:03d}] {msg['type']} ({msg['direction']}) - content[{i}]")
                    print(f"  ├─ Timestamp: {msg['timestamp']}")
                    print(f"  ├─ Content type: {content.get('type')}")
                    print(f"  ├─ Audio length: {content.get('_audio_length', 0)} chars")
                    
                    if 'transcript' in content:
                        print(f"  └─ Transcript: {content['transcript'][:100]}")
    
    if not audio_messages:
        print("\n⚠️  NO AUDIO DATA FOUND IN ANY MESSAGE!")
        print("\nPossible reasons:")
        print("  1. API configuration issue - audio modality not enabled")
        print("  2. Model doesn't support audio output")
        print("  3. Need to use different voice/parameters")
    else:
        print(f"\n✅ Found {len(audio_messages)} messages with audio data")
    
    # 详细查看 response.audio.* 消息
    print(f"\n{'='*70}")
    print("🔍 Detailed Analysis of response.audio.* messages:")
    print("-" * 70)
    
    audio_delta_msgs = [m for m in messages if m['type'] == 'response.audio.delta']
    audio_done_msgs = [m for m in messages if m['type'] == 'response.audio.done']
    
    print(f"\nresponse.audio.delta: {len(audio_delta_msgs)} messages")
    for msg in audio_delta_msgs:
        data = msg['data']
        has_audio = data.get('_audio_present', False)
        audio_len = data.get('_audio_length', 0)
        has_delta = data.get('_delta_present', False)
        delta_content = data.get('_delta_content', '')
        
        print(f"  [{msg['sequence']:03d}] has_audio={has_audio}, length={audio_len}, has_delta={has_delta}")
        if has_delta:
            print(f"       ⭐ delta content: {delta_content}")
        if not has_audio and not has_delta:
            print(f"       ⚠️  All fields: {list(data.keys())}")
    
    print(f"\nresponse.audio.done: {len(audio_done_msgs)} messages")
    for msg in audio_done_msgs:
        print(f"  [{msg['sequence']:03d}] {msg['timestamp']}")
        print(f"       Fields: {list(msg['data'].keys())}")
    
    # 查看 output_item.done 的详细结构
    print(f"\n{'='*70}")
    print("🔍 Detailed Analysis of response.output_item.done:")
    print("-" * 70)
    
    output_items = [m for m in messages if m['type'] == 'response.output_item.done']
    print(f"\nTotal: {len(output_items)} messages\n")
    
    for msg in output_items:
        item = msg['data'].get('item', {})
        content_list = item.get('content', [])
        
        print(f"[{msg['sequence']:03d}] {msg['timestamp']}")
        print(f"  Item ID: {item.get('id', 'N/A')}")
        print(f"  Item type: {item.get('type', 'N/A')}")
        print(f"  Content items: {len(content_list)}")
        
        for i, content in enumerate(content_list):
            print(f"    [{i}] type: {content.get('type')}")
            print(f"        keys: {list(content.keys())}")
            print(f"        has audio: {content.get('_audio_present', False)}")
            
            if content.get('_audio_present'):
                print(f"        audio length: {content.get('_audio_length')} chars")
            
            if 'transcript' in content:
                transcript = content['transcript']
                print(f"        transcript: {transcript[:80]}...")
        print()
    
    # 查看 session 配置
    print(f"\n{'='*70}")
    print("⚙️  Session Configuration:")
    print("-" * 70)
    
    session_msgs = [m for m in messages if m['type'] in ('session.update', 'session.created', 'session.updated')]
    for msg in session_msgs:
        print(f"\n{msg['type']} ({msg['direction']}):")
        session = msg['data'].get('session', {})
        
        important_fields = ['modalities', 'voice', 'output_audio_format', 
                           'input_audio_format', 'beta_fields']
        
        for field in important_fields:
            if field in session:
                print(f"  {field}: {session[field]}")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_log.py <log_file.jsonl>")
        sys.exit(1)
    
    log_file = sys.argv[1]
    analyze_log(log_file)