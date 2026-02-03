#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP服务器配置文件示例

此文件展示如何配置MCP服务器，包括API密钥等敏感信息。
请复制此文件为 config.py 并根据需要修改配置。
"""

import os
from pathlib import Path

# MCP服务器配置
MCP_CONFIG = {
    # 服务器配置
    'host': 'localhost',
    'port': 9999,

    # 数据目录配置
    'xtdata_dir': r'G:\国金证券QMT交易端\datadir',

    # API密钥配置（生产环境请使用强密码）
    # 方式1：直接设置
    'api_key': 'your-secure-api-key-here',

    # 方式2：从环境变量读取（推荐）
    # 'api_key': os.environ.get('XTDATA_MCP_API_KEY'),

    # 方式3：生成随机密钥（每次启动不同）
    # 'api_key': os.urandom(32).hex(),
}

# 客户端配置
CLIENT_CONFIG = {
    'server_url': f"http://{MCP_CONFIG['host']}:{MCP_CONFIG['port']}",
    'api_key': MCP_CONFIG['api_key'],
}

def load_config():
    """加载配置"""
    return MCP_CONFIG

def get_api_key():
    """获取API密钥"""
    # 优先级：环境变量 > 配置文件
    api_key = os.environ.get('XTDATA_MCP_API_KEY')
    if api_key:
        return api_key
    return MCP_CONFIG.get('api_key')

if __name__ == "__main__":
    print("MCP配置文件示例")
    print("=" * 50)
    print(f"服务器地址: {CLIENT_CONFIG['server_url']}")
    print(f"API密钥: {'已设置' if get_api_key() else '未设置'}")
    print()
    print("使用方法:")
    print("1. 复制此文件为 config.py")
    print("2. 修改其中的配置项")
    print("3. 在代码中导入: from config import MCP_CONFIG, get_api_key()")
    print()
    print("环境变量设置:")
    print("Windows: set XTDATA_MCP_API_KEY=your-key-here")
    print("Linux/Mac: export XTDATA_MCP_API_KEY=your-key-here")
    print("PowerShell: $env:XTDATA_MCP_API_KEY='your-key-here'")