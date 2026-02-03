#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥生成工具

生成安全的API密钥用于MCP服务器认证。
"""

import os
import secrets
import string
import argparse

def generate_secure_key(length=32):
    """生成安全的随机密钥"""
    # 使用密码学安全的随机数生成器
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=32):
    """生成十六进制密钥"""
    return secrets.token_hex(length)

def generate_url_safe_key(length=32):
    """生成URL安全的密钥"""
    return secrets.token_urlsafe(length)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成API密钥')
    parser.add_argument('--type', choices=['secure', 'hex', 'url-safe'],
                       default='secure', help='密钥类型')
    parser.add_argument('--length', type=int, default=32,
                       help='密钥长度')
    parser.add_argument('--env', action='store_true',
                       help='输出为环境变量设置格式')

    args = parser.parse_args()

    # 生成密钥
    if args.type == 'secure':
        key = generate_secure_key(args.length)
    elif args.type == 'hex':
        key = generate_hex_key(args.length // 2)  # hex是字节，所以长度减半
    elif args.type == 'url-safe':
        key = generate_url_safe_key(args.length // 4 * 3)  # base64编码

    print("生成的API密钥:"    print(f"  {key}")
    print()

    if args.env:
        print("环境变量设置:")
        if os.name == 'nt':  # Windows
            print(f"  set XTDATA_MCP_API_KEY={key}")
        else:  # Linux/Mac
            print(f"  export XTDATA_MCP_API_KEY={key}")
        print("  PowerShell: $env:XTDATA_MCP_API_KEY='{key}'")
    else:
        print("使用方法:")
        print("1. 服务器启动:")
        print(f"   python mcp/run_server.py --api-key \"{key}\"")
        print()
        print("2. 客户端连接:")
        print(f"   python mcp/client.py --api-key \"{key}\" --demo")
        print()
        print("3. 环境变量设置:")
        if os.name == 'nt':
            print(f"   set XTDATA_MCP_API_KEY={key}")
        else:
            print(f"   export XTDATA_MCP_API_KEY={key}")
        print("   PowerShell: $env:XTDATA_MCP_API_KEY='{key}'")

    print()
    print("安全提醒:")
    print("- 请妥善保管生成的密钥")
    print("- 定期更换密钥以增强安全性")
    print("- 生产环境使用强密码密钥")
    print("- 避免在代码中硬编码密钥")

if __name__ == "__main__":
    main()