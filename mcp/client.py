#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP客户端示例 - xtdata接口调用

演示如何通过HTTP调用MCP服务器的xtdata接口。
"""

import json
import sys
import os
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional


class XtDataMCPClient:
    """xtdata MCP客户端"""

    def __init__(self, server_url: str = "http://localhost:9696", api_key: Optional[str] = None):
        """初始化客户端

        Args:
            server_url: MCP服务器URL
            api_key: API密钥，用于认证
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        # 设置基础请求头
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # 如果提供了API密钥，添加到请求头
        if self.api_key:
            headers['X-API-Key'] = self.api_key
            print(f"已设置API密钥认证")

        self.session.headers.update(headers)
        print(f"MCP客户端初始化完成")
        print(f"服务器URL: {self.server_url}")
        print(f"认证状态: {'已启用' if self.api_key else '未启用'}")

    def check_server_status(self) -> bool:
        """检查服务器状态"""
        try:
            # 尝试连接到服务器根路径
            response = self.session.get(f"{self.server_url}/", timeout=5)
            print(f"服务器响应: {response.status_code}")
            return response.status_code < 500  # 任何非服务器错误都算连接成功
        except requests.exceptions.ConnectionError:
            print(f"连接失败: 无法连接到 {self.server_url}")
            return False
        except requests.exceptions.Timeout:
            print(f"连接超时: {self.server_url} 响应超时")
            return False
        except Exception as e:
            print(f"检查服务器状态时出错: {e}")
            return False

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

    def get_account_positions(self) -> Dict[str, Any]:
        """查看账户持仓情况"""
        print("调用 get_account_positions...")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "get_account_positions",
            "arguments": {}
        })
        return self._parse_response(response)

    def place_order(self, code: str, order_type: str, volume: int,
                   price: Optional[float] = None, price_type: str = "limit") -> Dict[str, Any]:
        """挂单

        Args:
            code: 股票代码，如 '000001' 或 '000001.SH'
            order_type: 委托类型，'buy' 或 'sell'
            volume: 委托数量
            price: 委托价格（限价单必填）
            price_type: 报价类型，'limit' 或 'market'
        """
        print(f"调用 place_order: {code}, {order_type}, 数量={volume}, 价格={price}, 类型={price_type}")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "place_order",
            "arguments": {
                "code": code,
                "order_type": order_type,
                "volume": volume,
                "price": price,
                "price_type": price_type
            }
        })
        return self._parse_response(response)

    def query_orders(self, strategy_name: Optional[str] = None,
                    order_type: Optional[str] = None,
                    status_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """查询订单成交情况"""
        print("调用 query_orders...")
        args = {}
        if strategy_name:
            args["strategy_name"] = strategy_name
        if order_type:
            args["order_type"] = order_type
        if status_list:
            args["status_list"] = status_list

        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "query_orders",
            "arguments": args
        })
        return self._parse_response(response)

    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """撤单"""
        print(f"调用 cancel_order: {order_id}")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "cancel_order",
            "arguments": {
                "order_id": order_id
            }
        })
        return self._parse_response(response)

    def list_tools(self) -> Dict[str, Any]:
        """列出可用工具"""
        print(f"连接到服务器: {self.server_url}")

        # 对于/tools/list，不发送请求体和Content-Type头
        headers = self.session.headers.copy()
        headers.pop('Content-Type', None)  # 移除Content-Type头

        try:
            response = self.session.post(f"{self.server_url}/tools/list", headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print(f"认证失败: {response.status_code} - 请检查API密钥")
                print(f"响应内容: {response.text}")
                return {}
            else:
                print(f"请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return {}
        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: 无法连接到服务器 {self.server_url}")
            print(f"请确保服务器正在运行，或检查服务器URL是否正确")
            print(f"错误详情: {e}")
            return {}
        except requests.exceptions.Timeout as e:
            print(f"连接超时: 服务器 {self.server_url} 响应超时")
            print(f"请检查服务器是否正在运行，或网络连接是否正常")
            print(f"错误详情: {e}")
            return {}
        except Exception as e:
            print(f"请求异常: {e}")
            return {}

    def _parse_response(self, response) -> Any:
        """解析HTTP响应"""
        try:
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    print(f"服务器错误: {data['error']}")
                    return None
                elif "result" in data:
                    return data["result"]
                else:
                    return data
            elif response.status_code == 401:
                print(f"认证失败: {response.status_code} - 请检查API密钥设置")
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        print(f"错误详情: {error_data['error']}")
                except:
                    print(f"响应内容: {response.text}")
                return None
            else:
                print(f"HTTP请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
        except requests.exceptions.JSONDecodeError:
            print(f"响应格式错误: 无法解析JSON响应")
            print(f"原始响应: {response.text}")
            return None
        except Exception as e:
            print(f"解析响应时出错: {e}")
            return None


def demo():
    """演示函数"""
    print("=== xtdata MCP客户端演示 ===\n")

    # 获取API密钥（环境变量）
    api_key = os.environ.get('XTDATA_MCP_API_KEY')

    # 创建客户端
    client = XtDataMCPClient("http://localhost:9999", api_key)

    # 检查服务器连接
    print("检查服务器连接...")
    if not client.check_server_status():
        print("❌ 无法连接到服务器，请检查：")
        print("   1. 服务器是否已启动: python mcp/run_server.py")
        print("   2. 服务器URL是否正确")
        print("   3. 防火墙和网络设置")
        return

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

        # 检查是否启用了交易功能
        tools_info = client.list_tools()
        has_trading = any(tool.get('name', '').startswith(('get_account_positions', 'place_order', 'query_orders', 'cancel_order'))
                        for tool in tools_info.get('tools', []))

        if has_trading:
            print("=== 交易功能演示 ===")
            print("\n⚠️  注意: 以下是交易功能演示，请谨慎使用！")

            print("5. 查看账户持仓:")
            positions = client.get_account_positions()
            if positions and "error" not in positions:
                print(f"   账户ID: {positions.get('account_id')}")
                print(f"   可用资金: {positions.get('cash', 0):.2f}")
                print(f"   持仓数量: {positions.get('positions_count', 0)}")
            else:
                print("   无法获取持仓信息或交易功能未启用\n")

            print("6. 查询订单:")
            orders = client.query_orders()
            if orders and "error" not in orders:
                print(f"   委托数量: {orders.get('orders_count', 0)}")
                print(f"   成交数量: {orders.get('trades_count', 0)}")
            else:
                print("   无法获取订单信息或交易功能未启用\n")

            print("💡 交易功能提示:")
            print("   - place_order: 挂单（限价/市价）")
            print("   - cancel_order: 撤单")
            print("   - 所有交易操作都会产生真实资金变动！")
        else:
            print("交易功能未启用，如需测试交易功能请使用 --enable-trade 参数启动服务器")

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
                       default='http://localhost:9696',
                       help='MCP服务器URL')
    parser.add_argument('--api-key', type=str, default="gfGOo0@Q8thvwta0Z*j^mGQqWgIM4Yrn",
                       help='API密钥，用于认证')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示模式')

    args = parser.parse_args()

    # 获取API密钥（优先级：命令行参数 > 环境变量）
    api_key = getattr(args, 'api_key', None)
    if not api_key:
        api_key = os.environ.get('XTDATA_MCP_API_KEY')

    print("=== xtdata MCP客户端配置 ===")
    print(f"服务器URL: {args.server_url}")
    print(f"API密钥来源: {'命令行参数' if getattr(args, 'api_key', None) else '环境变量' if api_key else '未设置'}")
    print(f"认证状态: {'已启用' if api_key else '未启用'}")
    print("-" * 40)

    if args.demo:
        # 运行演示
        demo()
    else:
        # 交互式客户端
        print("xtdata MCP客户端")
        print("输入 'help' 查看可用命令，输入 'quit' 退出")

        client = XtDataMCPClient(args.server_url, api_key)

        while True:
            try:
                cmd = input("> ").strip()

                if cmd == 'quit':
                    break
                elif cmd == 'help':
                    print("""
数据查询命令:
  sectors                    - 获取板块列表
  stocks <sector_name>       - 获取板块成份股
  tick <codes>               - 获取tick数据，如: tick 000001.SZ,600000.SH
  market <codes> [period]    - 获取市场数据，如: market 000001.SZ 1d
  tools                      - 列出可用工具

交易命令 (需要服务器启用交易功能):
  positions                  - 查看账户持仓
  buy CODE VOLUME [PRICE]    - 买入委托，如: buy 000001 100 10.5 (限价) 或 buy 000001 100 (市价)
  sell CODE VOLUME [PRICE]   - 卖出委托，如: sell 000001 100 10.5 (限价) 或 sell 000001 100 (市价)
  orders                     - 查询委托和成交记录
  cancel ORDER_ID            - 撤单，如: cancel 123456

⚠️  交易命令会产生真实资金变动，请谨慎使用！

其他命令:
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
                elif cmd == 'positions':
                    result = client.get_account_positions()
                    print(f"账户持仓: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif cmd.startswith('buy '):
                    # 格式: buy CODE VOLUME [PRICE]
                    parts = cmd[4:].strip().split()
                    if len(parts) < 2:
                        print("用法: buy CODE VOLUME [PRICE]")
                        continue
                    code = parts[0]
                    volume = int(parts[1])
                    price = float(parts[2]) if len(parts) > 2 else None
                    price_type = "limit" if price else "market"
                    result = client.place_order(code, "buy", volume, price, price_type)
                    print(f"买入委托: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif cmd.startswith('sell '):
                    # 格式: sell CODE VOLUME [PRICE]
                    parts = cmd[5:].strip().split()
                    if len(parts) < 2:
                        print("用法: sell CODE VOLUME [PRICE]")
                        continue
                    code = parts[0]
                    volume = int(parts[1])
                    price = float(parts[2]) if len(parts) > 2 else None
                    price_type = "limit" if price else "market"
                    result = client.place_order(code, "sell", volume, price, price_type)
                    print(f"卖出委托: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif cmd == 'orders':
                    result = client.query_orders()
                    print(f"订单查询: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif cmd.startswith('cancel '):
                    # 格式: cancel ORDER_ID
                    try:
                        order_id = int(cmd[7:].strip())
                        result = client.cancel_order(order_id)
                        print(f"撤单结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    except ValueError:
                        print("用法: cancel ORDER_ID (ORDER_ID必须是数字)")
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