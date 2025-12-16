import os
import sys
import time
import jwt
import requests
from datetime import datetime
from pprint import pprint

# --- 配置 ---
API_KEY = os.getenv("ZHIPU_API_KEY")
# 模型列表接口
MODELS_API_URL = "https://open.bigmodel.cn/api/paas/v4/models" 

# --- JWT Token 生成函数 ---

def generate_jwt_token(api_key: str, exp_seconds: int = 300) -> str:
    """
    使用智谱 API Key (ID.SECRET 格式) 生成 JWT Token。
    """
    try:
        api_key_id, api_key_secret = api_key.split('.')
    except ValueError:
        raise ValueError("API Key 格式错误。请确保格式为 'API_KEY_ID.API_KEY_SECRET'。")

    current_time = int(time.time())
    
    payload = {
        "api_key": api_key_id,
        "exp": current_time + exp_seconds, 
        "timestamp": current_time,
    }
    
    encoded_jwt = jwt.encode(
        payload,
        api_key_secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN_TYPE"}
    )
    return encoded_jwt

# --- 主程序逻辑 ---

def list_available_models():
    print("=== 智谱 AI 可用模型列表查询 ===")
    
    if not API_KEY:
        print("❌ 错误: 环境变量 ZHIPU_API_KEY 未设置。请先设置您的 API Key。")
        sys.exit(1)
        
    # 1. 生成 JWT Token
    try:
        auth_token = generate_jwt_token(API_KEY)
        print("✅ JWT Token 生成成功。")
    except Exception as e:
        print(f"❌ 错误: Token 生成失败: {e}")
        sys.exit(1)

    # 2. 调用模型列表 API
    print(f"🚀 正在请求模型列表 ({MODELS_API_URL})...")
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(MODELS_API_URL, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            
            print("\n✅ **查询成功！** 您当前可用的模型列表如下：")
            
            if models:
                # 提取模型名称和类型
                model_info = [{"id": m.get('id'), "object": m.get('object'), "owner": m.get('owner')} for m in models]
                
                # 打印列表
                for i, m in enumerate(model_info):
                    print(f"   {i+1}. ID: {m['id']} (类型: {m['object']})")
                
                # 如果需要看完整的原始数据，可以取消下面注释
                # print("\n--- 完整原始数据 (部分) ---")
                # pprint(models[:2]) # 打印前两个模型的详细信息
            else:
                print("   ⚠️ 模型列表为空。请检查您的账户是否已开通模型使用权限。")
                
        elif response.status_code == 401:
            error_msg = response.json().get('error', {}).get('message', '无详细信息')
            print("❌ **认证失败 (401 Unauthorized)。**")
            print(f"   错误信息: {error_msg}")
            print("   请注意：这是 API Key 或 Secret 错误的最有力证明。请检查您的 Key。")
            
        else:
            print(f"❌ **请求失败 ({response.status_code} 状态码)。**")
            print(f"   响应内容: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ **网络请求错误:** 无法连接到智谱 API。请检查您的网络连接或防火墙设置。")
        print(f"   详细错误: {e}")
        
    print("\n=== 查询结束 ===")

if __name__ == "__main__":
    list_available_models()