#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试认证功能
"""

import sys
import time
import requests
import threading
from pathlib import Path

# 设置路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_authentication():
    """测试认证功能"""
    print("测试MCP服务器认证功能...")

    # 测试API密钥
    test_api_key = "test-api-key-12345"

    # 启动启用认证的服务器
    from mcp.server import XtDataMCPServer

    server = XtDataMCPServer("localhost", 8005, api_key=test_api_key)
    server_thread = threading.Thread(target=lambda: server.serve_forever(), daemon=True)
    server_thread.start()

    # 等待服务器启动
    time.sleep(2)

    try:
        print("1. 测试无认证请求...")
        response = requests.post("http://localhost:8005/tools/list")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 401:
            print("   ✓ 正确拒绝无认证请求")
        else:
            print(f"   ✗ 意外的状态码: {response.status_code}")

        print("\n2. 测试错误的API密钥...")
        headers = {"X-API-Key": "wrong-key"}
        response = requests.post("http://localhost:8005/tools/list", headers=headers)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 401:
            print("   ✓ 正确拒绝错误的API密钥")
        else:
            print(f"   ✗ 意外的状态码: {response.status_code}")

        print("\n3. 测试正确的API密钥...")
        headers = {"X-API-Key": test_api_key}
        response = requests.post("http://localhost:8005/tools/list", headers=headers)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ 正确接受有效的API密钥")
            try:
                data = response.json()
                if "tools" in data:
                    print(f"   ✓ 返回了 {len(data['tools'])} 个工具")
            except:
                print("   ⚠ 响应格式异常")
        else:
            print(f"   ✗ 意外的状态码: {response.status_code}")

        print("\n4. 测试Bearer Token认证...")
        headers = {"Authorization": f"Bearer {test_api_key}"}
        response = requests.post("http://localhost:8005/tools/list", headers=headers)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Bearer Token认证成功")
        else:
            print(f"   ✗ Bearer Token认证失败: {response.status_code}")

    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        # 停止服务器
        server.stop()
        print("\n认证测试完成")

def test_no_auth():
    """测试无认证模式"""
    print("\n测试无认证模式...")

    # 启动无认证的服务器
    from mcp.server import XtDataMCPServer

    server = XtDataMCPServer("localhost", 8006)  # 不提供api_key
    server_thread = threading.Thread(target=lambda: server.serve_forever(), daemon=True)
    server_thread.start()

    # 等待服务器启动
    time.sleep(2)

    try:
        print("测试无认证服务器...")
        response = requests.post("http://localhost:8006/tools/list")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✓ 无认证模式正常工作")
        else:
            print(f"✗ 无认证模式异常: {response.status_code}")

    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        server.stop()

if __name__ == "__main__":
    test_authentication()
    test_no_auth()