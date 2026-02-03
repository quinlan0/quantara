#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP客户端示例 - xtdata接口调用

演示如何通过HTTP调用MCP服务器的xtdata接口。
"""

import json
import sys
import requests
from pathlib import Path
from typing import Any, Dict, List


class XtDataMCPClient:
    """xtdata MCP客户端"""

    def __init__(self, server_url: str = "http://localhost:9999"):
        """初始化客户端

        Args:
            server_url: MCP服务器URL
        """
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def get_sector_list(self) -> List[str]:
        """获取板块列表"""
        print("调用 get_sector_list...")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "get_sector_list",
            "arguments": {}
        })
        return self._parse_response(response)

    def get_stock_list_in_sector(self, sector_name: str, real_timetag: int = -1) -> List[str]:
        """获取板块成份股"""
        print(f"调用 get_stock_list_in_sector: {sector_name}")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "get_stock_list_in_sector",
            "arguments": {
                "sector_name": sector_name,
                "real_timetag": real_timetag
            }
        })
        return self._parse_response(response)

    def get_full_tick(self, code_list: List[str]) -> Dict[str, Any]:
        """获取盘口tick数据"""
        print(f"调用 get_full_tick: {code_list}")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "get_full_tick",
            "arguments": {"code_list": code_list}
        })
        return self._parse_response(response)

    def get_market_data_ex(self, stock_list: List[str], period: str = "1d",
                          count: int = 5) -> Dict[str, Any]:
        """获取市场数据"""
        print(f"调用 get_market_data_ex: {stock_list}, period={period}, count={count}")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "get_market_data_ex",
            "arguments": {
                "stock_list": stock_list,
                "period": period,
                "count": count
            }
        })
        return self._parse_response(response)

    def list_tools(self) -> Dict[str, Any]:
        """列出可用工具"""
        # 对于/tools/list，不发送请求体和Content-Type头
        headers = self.session.headers.copy()
        headers.pop('Content-Type', None)  # 移除Content-Type头

        response = self.session.post(f"{self.server_url}/tools/list", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return {}

    def _parse_response(self, response) -> Any:
        """解析HTTP响应"""
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                print(f"服务器错误: {data['error']}")
                return None
            elif "result" in data:
                return data["result"]
            else:
                return data
        else:
            print(f"HTTP请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None


def demo():
    """演示函数"""
    print("=== xtdata MCP客户端演示 ===\n")

    # 创建客户端
    client = XtDataMCPClient("http://localhost:9999")

    try:
        # 先列出可用工具
        print("可用工具:")
        tools = client.list_tools()
        if "tools" in tools:
            for tool in tools["tools"]:
                print(f"  - {tool['name']}: {tool['description']}")
        print()

        # 演示各个接口调用
        print("1. 获取板块列表:")
        sector_list = client.get_sector_list()
        print(f"   结果: {sector_list}\n")

        if sector_list and len(sector_list) > 0:
            print("2. 获取板块成份股:")
            stock_list = client.get_stock_list_in_sector(sector_list[0])
            print(f"   板块 '{sector_list[0]}' 的股票: {len(stock_list) if stock_list else 0} 只\n")

        print("3. 获取盘口tick数据:")
        tick_data = client.get_full_tick(["000001.SZ", "600000.SH"])
        print(f"   获取到 {len(tick_data) if tick_data else 0} 只股票的tick数据\n")

        print("4. 获取市场数据:")
        market_data = client.get_market_data_ex(["000001.SZ"], period="1d", count=3)
        print(f"   获取到 {len(market_data) if market_data else 0} 只股票的市场数据\n")

        print("=== 演示完成 ===")

    except Exception as e:
        print(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='xtdata MCP客户端')
    parser.add_argument('--server-url', type=str,
                       default='http://localhost:9999',
                       help='MCP服务器URL')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示模式')

    args = parser.parse_args()

    if args.demo:
        # 运行演示
        demo()
    else:
        # 交互式客户端
        print("xtdata MCP客户端")
        print("输入 'help' 查看可用命令，输入 'quit' 退出")

        client = XtDataMCPClient(args.server_url)

        while True:
            try:
                cmd = input("> ").strip()

                if cmd == 'quit':
                    break
                elif cmd == 'help':
                    print("""
可用命令:
  sectors                    - 获取板块列表
  stocks <sector_name>       - 获取板块成份股
  tick <codes>               - 获取tick数据，如: tick 000001.SZ,600000.SH
  market <codes> [period]    - 获取市场数据，如: market 000001.SZ 1d
  tools                      - 列出可用工具
  quit                       - 退出
                        """)
                elif cmd == 'sectors':
                    result = client.get_sector_list()
                    print(f"板块列表: {result}")
                elif cmd.startswith('stocks '):
                    sector_name = cmd[7:].strip()
                    result = client.get_stock_list_in_sector(sector_name)
                    print(f"板块 '{sector_name}' 的股票: {result}")
                elif cmd.startswith('tick '):
                    codes_str = cmd[5:].strip()
                    code_list = [code.strip() for code in codes_str.split(',')]
                    result = client.get_full_tick(code_list)
                    print(f"Tick数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif cmd.startswith('market '):
                    parts = cmd[7:].strip().split()
                    codes_str = parts[0]
                    period = parts[1] if len(parts) > 1 else '1d'
                    code_list = [code.strip() for code in codes_str.split(',')]
                    result = client.get_market_data_ex(code_list, period)
                    print(f"市场数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif cmd == 'tools':
                    result = client.list_tools()
                    print(f"可用工具: {json.dumps(result, indent=2, ensure_ascii=False)}")
                else:
                    print("未知命令，输入 'help' 查看帮助")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"命令执行出错: {e}")


if __name__ == "__main__":
    main()