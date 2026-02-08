#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易终端 - 命令行交易界面

提供简洁的命令行交易界面，每个命令只显示相关信息。
支持持仓查询、交易委托、订单查询等功能。
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    import requests
except ImportError as e:
    print(f"❌ 缺少必要的库: {e}")
    print("请安装: pip install rich")
    sys.exit(1)


class TradingTerminal:
    """交易终端 - 命令行交易界面"""

    def __init__(self, server_url: str = "http://localhost:9696", api_key: Optional[str] = None):
        """初始化交易终端

        Args:
            server_url: MCP服务器URL
            api_key: API密钥
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.console = Console()

        # 设置请求头
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key

        self.session.headers.update(headers)

        # 检查交易功能
        self._check_trading_available()

    def _check_trading_available(self):
        """检查交易功能是否可用"""
        try:
            response = self.session.post(f"{self.server_url}/tools/list", timeout=10)
            if response.status_code == 200:
                tools_data = response.json()
                trading_tools = [tool for tool in tools_data.get('tools', [])
                               if tool.get('name', '').startswith(('get_account_positions', 'place_order', 'query_orders', 'cancel_order'))]
                if trading_tools:
                    self.console.print(f"✅ 发现 {len(trading_tools)} 个交易工具", style="green")
                    return True
                else:
                    self.console.print("⚠️ 未发现交易工具，可能交易功能未启用", style="yellow")
                    return False
            else:
                self.console.print(f"❌ 无法连接到服务器: {response.status_code}", style="red")
                return False
        except Exception as e:
            self.console.print(f"❌ 连接服务器失败: {e}", style="red")
            return False

    def _make_request(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送API请求"""
        try:
            response = self.session.post(f"{self.server_url}/tools/call", json={
                "name": tool_name,
                "arguments": arguments
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    self.console.print(f"❌ 服务器错误: {data['error']}", style="red")
                    return None
                return data.get("result")
            else:
                self.console.print(f"❌ 请求失败: {response.status_code}", style="red")
                return None
        except Exception as e:
            self.console.print(f"❌ 请求异常: {e}", style="red")
            return None

    def show_positions(self):
        """显示账户持仓情况"""
        self.console.print("\n[bold blue]📊 查询账户持仓...[/bold blue]")

        positions_data = self._make_request("get_account_positions", {})
        if not positions_data or "error" in positions_data:
            return

        # 显示账户信息
        account_info = Panel(
            f"账户ID: {positions_data.get('account_id', 'N/A')}\n"
            f"可用资金: ¥{positions_data.get('cash', 0):,.2f}\n"
            f"冻结资金: ¥{positions_data.get('frozen_cash', 0):,.2f}\n"
            f"持仓市值: ¥{positions_data.get('market_value', 0):,.2f}\n"
            f"总资产: ¥{positions_data.get('total_asset', 0):,.2f}",
            title="💼 账户信息",
            border_style="blue"
        )
        self.console.print(account_info)

        # 显示持仓明细
        positions = positions_data.get('positions', [])
        if positions:
            table = Table(title="📈 持仓明细")
            table.add_column("股票代码", style="cyan", min_width=10)
            table.add_column("持仓量", justify="right", style="green", min_width=8)
            table.add_column("可用量", justify="right", style="green", min_width=8)
            table.add_column("成本价", justify="right", style="yellow", min_width=8)
            table.add_column("盈亏比", justify="right", style="red", min_width=8)
            table.add_column("盈亏额", justify="right", style="red", min_width=10)

            for pos in positions:
                code = pos.get('code', '')
                volume = pos.get('volume', 0)
                can_use_volume = pos.get('can_use_volume', 0)
                avg_price = pos.get('avg_price', 0)

                # 模拟当前价格（实际应用中应该从实时数据获取）
                current_price = avg_price  # 这里用成本价代替
                profit_ratio = 0.0 if avg_price == 0 else (current_price - avg_price) / avg_price * 100
                profit_amount = (current_price - avg_price) * volume

                table.add_row(
                    code,
                    f"{volume:,}",
                    f"{can_use_volume:,}",
                    f"¥{avg_price:.2f}",
                    f"{profit_ratio:+.2f}%",
                    f"¥{profit_amount:+,.2f}"
                )

            self.console.print(table)
        else:
            self.console.print("[yellow]📭 当前无持仓[/yellow]")

    def place_buy_order(self, code: str, volume: int, price: Optional[float] = None):
        """买入委托"""
        price_type = "limit" if price else "market"
        self.console.print(f"\n[bold green]📈 买入委托: {code} {volume}股 @ {price if price else '市价'} ({price_type})[/bold green]")

        result = self._make_request("place_order", {
            "code": code,
            "order_type": "buy",
            "volume": volume,
            "price": price,
            "price_type": price_type
        })

        if result and "error" not in result:
            # 显示委托结果
            table = Table(title="✅ 买入委托结果")
            table.add_column("字段", style="cyan")
            table.add_column("值", style="green")

            table.add_row("订单ID", str(result.get('order_id', 'N/A')))
            table.add_row("股票代码", result.get('code', 'N/A'))
            table.add_row("委托类型", "买入")
            table.add_row("委托数量", str(result.get('volume', 0)))
            table.add_row("委托价格", str(result.get('price', '市价')))
            table.add_row("报价类型", result.get('price_type', 'N/A'))
            table.add_row("状态", result.get('status', 'N/A'))

            self.console.print(table)
        else:
            self.console.print("[red]❌ 买入委托失败[/red]")

    def place_sell_order(self, code: str, volume: int, price: Optional[float] = None):
        """卖出委托"""
        price_type = "limit" if price else "market"
        self.console.print(f"\n[bold red]📉 卖出委托: {code} {volume}股 @ {price if price else '市价'} ({price_type})[/bold red]")

        result = self._make_request("place_order", {
            "code": code,
            "order_type": "sell",
            "volume": volume,
            "price": price,
            "price_type": price_type
        })

        if result and "error" not in result:
            # 显示委托结果
            table = Table(title="✅ 卖出委托结果")
            table.add_column("字段", style="cyan")
            table.add_column("值", style="red")

            table.add_row("订单ID", str(result.get('order_id', 'N/A')))
            table.add_row("股票代码", result.get('code', 'N/A'))
            table.add_row("委托类型", "卖出")
            table.add_row("委托数量", str(result.get('volume', 0)))
            table.add_row("委托价格", str(result.get('price', '市价')))
            table.add_row("报价类型", result.get('price_type', 'N/A'))
            table.add_row("状态", result.get('status', 'N/A'))

            self.console.print(table)
        else:
            self.console.print("[red]❌ 卖出委托失败[/red]")

    def show_orders(self):
        """显示所有订单"""
        self.console.print("\n[bold blue]📋 查询订单...[/bold blue]")

        orders_data = self._make_request("query_orders", {})
        if not orders_data or "error" in orders_data:
            return

        orders = orders_data.get('orders', [])
        trades = orders_data.get('trades', [])

        if orders:
            table = Table(title=f"📝 当前委托 ({len(orders)}个)")
            table.add_column("订单ID", style="cyan", min_width=10)
            table.add_column("股票代码", style="white", min_width=10)
            table.add_column("类型", style="green", min_width=6)
            table.add_column("数量", justify="right", style="yellow", min_width=8)
            table.add_column("价格", justify="right", style="yellow", min_width=10)
            table.add_column("状态", style="red", min_width=8)
            table.add_column("时间", style="dim", min_width=19)

            for order in orders:
                order_time_str = order.get('order_time', '')
                if order_time_str:
                    try:
                        if isinstance(order_time_str, str):
                            order_time = datetime.fromisoformat(order_time_str.replace('Z', '+00:00'))
                        else:
                            order_time = order_time_str
                        time_str = order_time.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = str(order_time_str)[:19]
                else:
                    time_str = 'N/A'

                table.add_row(
                    str(order.get('order_id', 0)),
                    order.get('code', ''),
                    order.get('order_type', ''),
                    str(order.get('volume', 0)),
                    f"{order.get('price', 0):.2f}",
                    order.get('order_status', ''),
                    time_str
                )

            self.console.print(table)

        if trades:
            trade_table = Table(title=f"💰 今日成交 ({len(trades)}笔)")
            trade_table.add_column("成交ID", style="cyan", min_width=12)
            trade_table.add_column("订单ID", style="white", min_width=10)
            trade_table.add_column("股票代码", style="white", min_width=10)
            trade_table.add_column("类型", style="green", min_width=6)
            trade_table.add_column("数量", justify="right", style="yellow", min_width=8)
            trade_table.add_column("价格", justify="right", style="yellow", min_width=10)
            trade_table.add_column("金额", justify="right", style="yellow", min_width=12)
            trade_table.add_column("时间", style="dim", min_width=19)

            for trade in trades:
                traded_time_str = trade.get('traded_time', '')
                if traded_time_str:
                    try:
                        if isinstance(traded_time_str, str):
                            traded_time = datetime.fromisoformat(traded_time_str.replace('Z', '+00:00'))
                        else:
                            traded_time = traded_time_str
                        time_str = traded_time.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = str(traded_time_str)[:19]
                else:
                    time_str = 'N/A'

                trade_table.add_row(
                    str(trade.get('traded_id', '')),
                    str(trade.get('order_id', 0)),
                    trade.get('code', ''),
                    trade.get('order_type', ''),
                    str(trade.get('traded_volume', 0)),
                    f"{trade.get('traded_price', 0):.2f}",
                    f"¥{trade.get('traded_amount', 0):,.2f}",
                    time_str
                )

            self.console.print(trade_table)

        if not orders and not trades:
            self.console.print("[yellow]📭 当前无订单记录[/yellow]")

    def cancel_order(self, order_id: int):
        """撤单"""
        self.console.print(f"\n[bold yellow]🚫 撤单: {order_id}[/bold yellow]")

        result = self._make_request("cancel_order", {"order_id": order_id})

        if result and "error" not in result:
            self.console.print(f"[green]✅ 撤单请求已提交: {order_id}[/green]")
        else:
            self.console.print("[red]❌ 撤单失败[/red]")

    def show_help(self):
        """显示帮助信息"""
        help_text = """
[bold cyan]交易终端命令[/bold cyan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold green]交易命令:[/bold green]
  buy CODE VOLUME [PRICE]    - 买入委托
  sell CODE VOLUME [PRICE]   - 卖出委托
  cancel ORDER_ID            - 撤单

[bold blue]查询命令:[/bold blue]
  positions                  - 查看持仓信息
  orders                     - 查看订单记录

[bold yellow]其他:[/bold yellow]
  help                       - 显示帮助
  quit                       - 退出终端
        """
        self.console.print(Panel(help_text, title="📖 帮助", border_style="blue"))

    def run(self):
        """运行交易终端"""
        # 显示欢迎信息
        self.console.print("[bold green]🚀 交易终端启动[/bold green]")
        self.console.print("[yellow]输入 'help' 查看命令帮助，输入 'quit' 退出[/yellow]")
        self.console.print("[red]⚠️  注意: 所有交易操作都会产生真实资金变动！[/red]")

        try:

            while True:
                command = self.console.input("\n[bold cyan]交易> [/bold cyan]").strip()

                if not command:
                    continue

                if command.lower() in ['quit', 'q']:
                    break
                elif command.lower() in ['help', 'h']:
                    self.show_help()
                elif command == 'positions':
                    self.show_positions()
                elif command.startswith('buy '):
                    # 格式: buy CODE VOLUME [PRICE]
                    parts = command[4:].strip().split()
                    if len(parts) < 2:
                        self.console.print("[red]❌ 用法: buy CODE VOLUME [PRICE][/red]")
                        continue

                    code = parts[0]
                    try:
                        volume = int(parts[1])
                        price = float(parts[2]) if len(parts) > 2 else None
                    except ValueError:
                        self.console.print("[red]❌ 数量和价格必须是数字[/red]")
                        continue

                    self.place_buy_order(code, volume, price)
                elif command.startswith('sell '):
                    # 格式: sell CODE VOLUME [PRICE]
                    parts = command[5:].strip().split()
                    if len(parts) < 2:
                        self.console.print("[red]❌ 用法: sell CODE VOLUME [PRICE][/red]")
                        continue

                    code = parts[0]
                    try:
                        volume = int(parts[1])
                        price = float(parts[2]) if len(parts) > 2 else None
                    except ValueError:
                        self.console.print("[red]❌ 数量和价格必须是数字[/red]")
                        continue

                    self.place_sell_order(code, volume, price)
                elif command == 'orders':
                    self.show_orders()
                elif command.startswith('cancel '):
                    # 格式: cancel ORDER_ID
                    try:
                        order_id = int(command[7:].strip())
                        self.cancel_order(order_id)
                    except ValueError:
                        self.console.print("[red]❌ 用法: cancel ORDER_ID (ORDER_ID必须是数字)[/red]")
                else:
                    self.console.print(f"[yellow]❓ 未知命令: {command} (输入 'help' 查看帮助)[/yellow]")

        except KeyboardInterrupt:
            pass
        finally:
            self.console.print("\n[bold yellow]👋 交易终端已退出[/bold yellow]")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='交易终端 - 命令行交易界面')
    parser.add_argument('--server-url', type=str,
                        default='http://localhost:9696',
                        help='MCP服务器地址 (默认: http://localhost:9696)')
    parser.add_argument('--api-key', type=str, default="gfGOo0@Q8thvwta0Z*j^mGQqWgIM4Yrn",
                        help='API密钥')

    args = parser.parse_args()

    if not args.api_key:
        print("❌ 需要提供API密钥: --api-key")
        return

    # 创建并运行交易终端
    terminal = TradingTerminal(args.server_url, args.api_key)
    terminal.run()


if __name__ == "__main__":
    main()