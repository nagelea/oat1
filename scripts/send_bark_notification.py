#!/usr/bin/env python3
"""
Bark 快速测试脚本
用于验证 Bark 配置是否正确
"""

import requests
import os
import json
from datetime import datetime


def test_bark_simple():
    """简单的 Bark 测试"""
    bark_key = os.environ.get('BARK_KEY')
    bark_server = os.environ.get('BARK_SERVER', 'https://api.day.app')
    
    if not bark_key:
        print("❌ 请设置 BARK_KEY 环境变量")
        return False
    
    # 确保服务器地址格式正确
    if not bark_server.startswith('http'):
        bark_server = f'https://{bark_server}'
    
    if bark_server.endswith('/'):
        bark_server = bark_server.rstrip('/')
    
    print(f"📱 测试 Bark 通知...")
    print(f"🔗 服务器: {bark_server}")
    print(f"🔑 Key: {bark_key[:8]}...")
    
    # 方法1: 使用 POST 请求 (推荐)
    print("\n🧪 方法1: POST 请求测试")
    success1 = test_post_method(bark_server, bark_key)
    
    # 方法2: 使用简单的 GET 请求
    print("\n🧪 方法2: GET 请求测试")
    success2 = test_get_method(bark_server, bark_key)
    
    return success1 or success2


def test_post_method(bark_server, bark_key):
    """测试 POST 方法"""
    try:
        url = f"{bark_server}/{bark_key}"
        
        data = {
            'title': '🧪 Bark 测试',
            'body': f'测试时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n这是一条测试消息。',
            'level': 'passive',
            'sound': 'birdsong'
        }
        
        print(f"📤 POST URL: {url}")
        print(f"📋 数据: {data}")
        
        response = requests.post(url, json=data, timeout=10)
        
        print(f"📊 状态码: {response.status_code}")
        print(f"📄 响应: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('code') == 200:
                    print("✅ POST 方法测试成功!")
                    return True
                else:
                    print(f"❌ 服务器返回错误: {result}")
                    return False
            except:
                # 有些 Bark 服务器可能不返回 JSON
                if 'success' in response.text.lower():
                    print("✅ POST 方法测试成功! (非JSON响应)")
                    return True
                else:
                    print("❌ 响应格式异常")
                    return False
        else:
            print(f"❌ POST 方法失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ POST 方法异常: {e}")
        return False


def test_get_method(bark_server, bark_key):
    """测试 GET 方法"""
    try:
        from urllib.parse import quote
        
        title = "🧪 Bark GET测试"
        message = f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # URL 编码
        encoded_title = quote(title.encode('utf-8'))
        encoded_message = quote(message.encode('utf-8'))
        
        url = f"{bark_server}/{bark_key}/{encoded_title}/{encoded_message}"
        params = {
            'level': 'passive',
            'sound': 'birdsong'
        }
        
        print(f"📤 GET URL: {url}")
        print(f"📋 参数: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"📊 状态码: {response.status_code}")
        print(f"📄 响应: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('code') == 200:
                    print("✅ GET 方法测试成功!")
                    return True
                else:
                    print(f"❌ 服务器返回错误: {result}")
                    return False
            except:
                print("✅ GET 方法测试成功! (非JSON响应)")
                return True
        else:
            print(f"❌ GET 方法失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ GET 方法异常: {e}")
        return False


def test_with_curl():
    """提供 curl 命令进行手动测试"""
    bark_key = os.environ.get('BARK_KEY')
    bark_server = os.environ.get('BARK_SERVER', 'https://api.day.app')
    
    if not bark_key:
        print("❌ 请设置 BARK_KEY 环境变量")
        return
    
    if bark_server.endswith('/'):
        bark_server = bark_server.rstrip('/')
    
    print("\n🔧 手动测试命令:")
    print("你可以在终端中运行以下命令进行手动测试:\n")
    
    # POST 方法
    print("1. POST 方法:")
    curl_post = f'''curl -X POST "{bark_server}/{bark_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"title": "🧪 手动测试", "body": "这是手动测试消息", "level": "passive"}}\''''
    print(curl_post)
    
    # GET 方法
    print("\n2. GET 方法:")
    curl_get = f'curl "{bark_server}/{bark_key}/🧪%20手动测试/这是手动测试消息?level=passive"'
    print(curl_get)
    
    print("\n如果上述命令成功，你应该会收到 Bark 通知。")


def main():
    """主函数"""
    print("🚀 Bark 配置测试工具")
    print("=" * 50)
    
    # 检查环境变量
    bark_key = os.environ.get('BARK_KEY')
    bark_server = os.environ.get('BARK_SERVER', 'https://api.day.app')
    
    if not bark_key:
        print("❌ 错误: 未设置 BARK_KEY 环境变量")
        print("\n💡 设置方法:")
        print("export BARK_KEY='your_bark_key'")
        print("export BARK_SERVER='https://api.day.app'  # 可选")
        return
    
    print(f"✅ BARK_KEY: {bark_key[:8]}...")
    print(f"✅ BARK_SERVER: {bark_server}")
    
    # 运行测试
    success = test_bark_simple()
    
    if success:
        print("\n🎉 Bark 配置测试成功!")
        print("现在你可以在 GitHub Actions 中正常使用 Bark 通知了。")
    else:
        print("\n❌ Bark 配置测试失败!")
        print("\n🔧 故障排除建议:")
        print("1. 检查 BARK_KEY 是否正确")
        print("2. 确认 Bark App 正在运行")
        print("3. 检查网络连接")
        print("4. 尝试手动测试命令")
        
        # 提供手动测试命令
        test_with_curl()


if __name__ == "__main__":
    main()
