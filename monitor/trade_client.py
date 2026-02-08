#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行交易客户端 - 通过MCP服务进行交易操作

连接到MCP服务器，提供命令行界面进行股票交易操作。
支持查看持仓、挂单、查询订单、撤单等功能。
"""

import json
import sys
import os
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class TradeClient:
    """交易客户端 - 连接MCP服务器进行交易操作"""

    def __init__(self, server_url: str = "http://localhost:9696", api_key: Optional[str] = None):
        """初始化交易客户端

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
        print(f"交易客户端初始化完成")
        print(f"服务器URL: {self.server_url}")
        print(f"认证状态: {'已启用' if self.api_key else '未启用'}")

        # 检查交易功能是否可用
        self._check_trading_available()

    def _check_trading_available(self):
        """检查交易功能是否可用"""
        try:
            response = self.session.post(f"{self.server_url}/tools/list", timeout=10)
            if response.status_code == 200:
                tools_data = response.json()
                if 'tools' in tools_data:
                    trading_tools = [tool for tool in tools_data['tools']
                                   if tool.get('name', '').startswith(('get_account_positions', 'place_order', 'query_orders', 'cancel_order'))]
                    if trading_tools:
                        print(f"✅ 发现 {len(trading_tools)} 个交易工具")
                        return True
                    else:
                        print("⚠️  未发现交易工具，可能交易功能未启用")
                        return False
                else:
                    print("❌ 无法获取工具列表")
                    return False
            else:
                print(f"❌ 服务器响应错误: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 连接服务器失败: {e}")
            return False

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

    def get_account_positions(self) -> Dict[str, Any]:
        """查看账户持仓情况"""
        print("\n📊 查询账户持仓...")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "get_account_positions",
            "arguments": {}
        })
        result = self._parse_response(response)
        if result and 'error' not in result:
            self._display_positions(result)
        return result

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
        print(f"\n📝 挂单: {code} {order_type} {volume}股 @ {price if price else '市价'} ({price_type})")
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
        result = self._parse_response(response)
        if result and 'error' not in result:
            self._display_order_result(result)
        return result

    def query_orders(self) -> Dict[str, Any]:
        """查询订单成交情况"""
        print("\n📋 查询订单...")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "query_orders",
            "arguments": {}
        })
        result = self._parse_response(response)
        if result and 'error' not in result:
            self._display_orders(result)
        return result

    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """撤单"""
        print(f"\n🚫 撤单: {order_id}")
        response = self.session.post(f"{self.server_url}/tools/call", json={
            "name": "cancel_order",
            "arguments": {
                "order_id": order_id
            }
        })
        result = self._parse_response(response)
        if result and 'error' not in result:
            print("✅ 撤单请求已提交")
        return result

    def _parse_response(self, response) -> Any:
        """解析HTTP响应"""
        try:
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    print(f"❌ 服务器错误: {data['error']}")
                    return None
                elif "result" in data:
                    return data["result"]
                else:
                    return data
            elif response.status_code == 401:
                print(f"❌ 认证失败: {response.status_code} - 请检查API密钥设置")
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        print(f"错误详情: {error_data['error']}")
                except:
                    print(f"响应内容: {response.text}")
                return None
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
        except requests.exceptions.JSONDecodeError:
            print(f"❌ 响应格式错误: 无法解析JSON响应")
            print(f"原始响应: {response.text}")
            return None
        except Exception as e:
            print(f"❌ 解析响应时出错: {e}")
            return None

    def _display_positions(self, positions: Dict[str, Any]):
        """显示持仓信息"""
        if not positions:
            print("📭 无持仓信息")
            return

        print("\n💼 账户持仓情况:")
        print(f"账户ID: {positions.get('account_id', 'N/A')}")
        print(f"可用资金: ¥{positions.get('cash', 0):,.2f}")
        print(f"冻结资金: ¥{positions.get('frozen_cash', 0):,.2f}")
        print(f"持仓市值: ¥{positions.get('market_value', 0):,.2f}")
        print(f"总资产: ¥{positions.get('total_asset', 0):,.2f}")

        position_list = positions.get('positions', [])
        if position_list:
            print(f"\n📈 持仓明细 ({len(position_list)} 只股票):")
            print("-" * 80)
            print(f"{'股票代码':<10} {'股票名称':<10} {'持仓数量':<10} {'可用数量':<10} {'成本价':<10} {'市值':<12}")
            print("-" * 80)
            for pos in position_list:
                print(f"{pos.get('code', ''):<10} {'N/A':<10} {pos.get('volume', 0):<10} {pos.get('can_use_volume', 0):<10} {pos.get('avg_price', 0):<10.2f} ¥{pos.get('market_value', 0):<10,.2f}")
        else:
            print("\n📭 当前无持仓")

    def _display_order_result(self, order_result: Dict[str, Any]):
        """显示挂单结果"""
        if not order_result:
            return

        print("\n✅ 挂单结果:")
        print(f"订单ID: {order_result.get('order_id', 'N/A')}")
        print(f"股票代码: {order_result.get('code', 'N/A')}")
        print(f"委托类型: {order_result.get('order_type', 'N/A')}")
        print(f"委托数量: {order_result.get('volume', 0)}")
        print(f"委托价格: {order_result.get('price', '市价')}")
        print(f"报价类型: {order_result.get('price_type', 'N/A')}")
        print(f"状态: {order_result.get('status', 'N/A')}")

    def _display_orders(self, orders_data: Dict[str, Any]):
        """显示订单信息"""
        if not orders_data:
            print("📭 无订单信息")
            return

        orders = orders_data.get('orders', [])
        trades = orders_data.get('trades', [])

        print(f"\n📋 订单概览: {len(orders)} 个委托, {len(trades)} 笔成交")

        if orders:
            print("\n📝 当前委托:")
            print("-" * 100)
            print(f"{'订单ID':<10} {'股票代码':<10} {'类型':<6} {'数量':<8} {'价格':<10} {'状态':<8} {'时间':<19}")
            print("-" * 100)
            for order in orders:
                order_time = order.get('order_time', '')
                if order_time:
                    try:
                        # 尝试格式化时间显示
                        dt = datetime.fromisoformat(str(order_time))
                        time_str = dt.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = str(order_time)[:19]
                else:
                    time_str = 'N/A'
                print(f"{order.get('order_id', 0):<10} {order.get('code', ''):<10} {order.get('order_type', ''):<6} {order.get('volume', 0):<8} {order.get('price', 0):<10.2f} {order.get('order_status', ''):<8} {time_str:<19}")

        if trades:
            print("\n💰 今日成交:")
            print("-" * 100)
            print(f"{'成交ID':<12} {'订单ID':<10} {'股票代码':<10} {'类型':<6} {'数量':<8} {'价格':<10} {'金额':<12} {'时间':<19}")
            print("-" * 100)
            for trade in trades:
                traded_time = trade.get('traded_time', '')
                if traded_time:
                    try:
                        dt = datetime.fromisoformat(str(traded_time))
                        time_str = dt.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = str(traded_time)[:19]
                else:
                    time_str = 'N/A'
                print(f"{trade.get('traded_id', ''):<12} {trade.get('order_id', 0):<10} {trade.get('code', ''):<10} {trade.get('order_type', ''):<6} {trade.get('traded_volume', 0):<8} {trade.get('traded_price', 0):<10.2f} ¥{trade.get('traded_amount', 0):<10,.2f} {time_str:<19}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='命令行交易客户端')
    parser.add_argument('--server-url', type=str,
                       default='http://localhost:9696',
                       help='MCP服务器URL')
    parser.add_argument('--api-key', type=str,
                       help='API密钥，用于认证。如果不提供则尝试从环境变量读取')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示模式，展示各项功能')

    args = parser.parse_args()

    # 获取API密钥（优先级：命令行参数 > 环境变量）
    api_key = getattr(args, 'api_key', None)
    if not api_key:
        api_key = os.environ.get('XTDATA_MCP_API_KEY')

    print("=== 命令行交易客户端 ===")
    print(f"服务器URL: {args.server_url}")
    print(f"API密钥来源: {'命令行参数' if getattr(args, 'api_key', None) else '环境变量' if api_key else '未设置'}")
    print(f"认证状态: {'已启用' if api_key else '未启用'}")
    print("-" * 50)

    if args.demo:
        # 运行演示
        demo_trading(args.server_url, api_key)
    else:
        # 交互式交易客户端
        print("交易客户端 - 连接到MCP服务器进行交易操作")
        print("输入 'help' 查看可用命令，输入 'quit' 退出")
        print("\n⚠️  重要提醒:")
        print("   - 所有交易操作都会产生真实资金变动")
        print("   - 请确保您了解交易风险")
        print("   - 建议先在模拟环境测试")

        client = TradeClient(args.server_url, api_key)

        while True:
            try:
                cmd = input("\n交易> ").strip()

                if cmd == 'quit':
                    break
                elif cmd == 'help':
                    show_help()
                elif cmd == 'positions':
                    client.get_account_positions()
                elif cmd.startswith('buy '):
                    # 格式: buy CODE VOLUME [PRICE]
                    parts = cmd[4:].strip().split()
                    if len(parts) < 2:
                        print("❌ 用法: buy CODE VOLUME [PRICE]")
                        continue
                    code = parts[0]
                    volume = int(parts[1])
                    price = float(parts[2]) if len(parts) > 2 else None
                    price_type = "limit" if price else "market"
                    client.place_order(code, "buy", volume, price, price_type)
                elif cmd.startswith('sell '):
                    # 格式: sell CODE VOLUME [PRICE]
                    parts = cmd[5:].strip().split()
                    if len(parts) < 2:
                        print("❌ 用法: sell CODE VOLUME [PRICE]")
                        continue
                    code = parts[0]
                    volume = int(parts[1])
                    price = float(parts[2]) if len(parts) > 2 else None
                    price_type = "limit" if price else "market"
                    client.place_order(code, "sell", volume, price, price_type)
                elif cmd == 'orders':
                    client.query_orders()
                elif cmd.startswith('cancel '):
                    # 格式: cancel ORDER_ID
                    try:
                        order_id = int(cmd[7:].strip())
                        client.cancel_order(order_id)
                    except ValueError:
                        print("❌ 用法: cancel ORDER_ID (ORDER_ID必须是数字)")
                elif cmd == 'status':
                    if client.check_server_status():
                        print("✅ 服务器连接正常")
                    else:
                        print("❌ 服务器连接失败")
                else:
                    print("❓ 未知命令，输入 'help' 查看帮助")

            except KeyboardInterrupt:
                print("\n👋 退出交易客户端")
                break
            except Exception as e:
                print(f"❌ 命令执行出错: {e}")


def show_help():
    """显示帮助信息"""
    print("""
交易命令帮助:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

数据查询:
  positions         - 查看账户持仓情况
  orders            - 查询委托和成交记录
  status            - 检查服务器连接状态

交易命令 (⚠️ 会产生真实资金变动):
  buy CODE VOLUME [PRICE]    - 买入委托
                               示例: buy 000001 100 10.50  (限价买入)
                               示例: buy 000001 100        (市价买入)

  sell CODE VOLUME [PRICE]   - 卖出委托
                               示例: sell 000001 100 10.50 (限价卖出)
                               示例: sell 000001 100       (市价卖出)

  cancel ORDER_ID           - 撤单
                               示例: cancel 123456

其他命令:
  help                     - 显示此帮助信息
  quit                     - 退出交易客户端

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

重要安全提醒:
⚠️ 所有交易命令都会在真实账户上执行操作！
⚠️ 请确保:
   1. 服务器已启用交易功能 (--enable-trade)
   2. 账户资金充足
   3. 理解交易风险
   4. 先在模拟环境测试

示例使用流程:
1. positions          # 查看当前持仓
2. buy 000001 100     # 市价买入100股平安银行
3. orders             # 查看委托状态
4. cancel 123456      # 如需要，撤回委托
    """)


def demo_trading(server_url: str, api_key: Optional[str]):
    """演示交易功能"""
    print("=== 交易功能演示 ===\n")

    client = TradeClient(server_url, api_key)

    # 检查服务器连接
    print("检查服务器连接...")
    if not client.check_server_status():
        print("❌ 无法连接到服务器，请检查：")
        print("   1. 服务器是否已启动: python mcp/run_server.py --enable-trade")
        print("   2. 服务器URL是否正确")
        print("   3. 防火墙和网络设置")
        return

    try:
        print("开始演示交易功能...\n")

        # 1. 查看持仓
        print("1️⃣ 查看账户持仓")
        positions = client.get_account_positions()
        if positions and 'error' in positions:
            print("⚠️  无法获取持仓信息，可能需要启用交易功能")
            return

        # 2. 查询订单
        print("\n2️⃣ 查询当前订单")
        orders = client.query_orders()

        print("\n=== 演示完成 ===")
        print("💡 如需实际交易，请使用交互模式并谨慎操作！")

    except Exception as e:
        print(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()