#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
启动xtdata MCP服务器

使用方法:
python run_server.py --xtdata-dir "G:\国金证券QMT交易端\datadir"
"""

import sys
import os
from pathlib import Path

def main():
    """启动MCP服务器"""
    import argparse

    parser = argparse.ArgumentParser(description='启动xtdata MCP服务器')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=9696,
                       help='服务器端口')
    parser.add_argument('--xtdata-dir', type=str,
                       default=r'G:\国金证券QMT交易端\datadir',
                       help='xtdata数据目录路径')
    parser.add_argument('--api-key', type=str, default='gfGOo0@Q8thvwta0Z*j^mGQqWgIM4Yrn',
                       help='API密钥，用于认证。如果不提供则不启用认证')

    args = parser.parse_args()

    # 导入服务器模块
    try:
        from server import XtDataMCPServer
    except ImportError:
        print("错误: 无法导入服务器模块")
        print(f"请确保在正确的目录运行: {Path(__file__).parent}")
        return 1

    print("启动xtdata MCP服务器...")
    print(f"主机地址: {args.host}")
    print(f"端口: {args.port}")
    print(f"api_key:: {args.api_key}")
    print(f"数据目录: {args.xtdata_dir}")
    print("-" * 50)

    try:
        # 获取API密钥（优先级：命令行参数 > 环境变量）
        api_key = getattr(args, 'api_key', None)

        # 创建并启动服务器
        server = XtDataMCPServer(args.host, args.port, args.xtdata_dir, api_key)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动服务器失败: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())