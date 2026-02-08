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
    parser.add_argument('--enable-trade', action='store_true',
                       help='启用交易功能')
    parser.add_argument('--trader-path', type=str,
                       default=r'G:\国金证券QMT交易端\userdata_mini',
                       help='交易器数据目录路径')
    parser.add_argument('--account-id', type=str, default='8887181228',
                       help='交易账户ID')
    parser.add_argument('--session-id', type=int, default=123456,
                       help='交易会话ID')

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
    print(f"API密钥: {'已设置' if args.api_key else '未设置'}")
    print(f"数据目录: {args.xtdata_dir}")
    print(f"交易功能: {'已启用' if args.enable_trade else '未启用'}")

    if args.enable_trade:
        print(f"交易器路径: {args.trader_path}")
        print(f"账户ID: {args.account_id}")
        print(f"会话ID: {args.session_id}")

        print("\n⚠️  交易功能已启用，请确保：")
        print("   1. QMT交易终端正在运行")
        print("   2. 交易账户资金充足")
        print("   3. 网络连接稳定")
        print("   4. 仅在测试环境使用")

    print("-" * 50)

    try:
        # 获取API密钥（优先级：命令行参数 > 环境变量）
        api_key = getattr(args, 'api_key', None)

        # 创建并启动服务器
        server = XtDataMCPServer(
            host=args.host,
            port=args.port,
            xtdata_dir=args.xtdata_dir,
            api_key=api_key,
            enable_trade=args.enable_trade,
            trader_path=args.trader_path,
            session_id=args.session_id,
            account_id=args.account_id
        )
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动服务器失败: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())