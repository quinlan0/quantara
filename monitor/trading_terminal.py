#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易终端 - 实时交易界面

提供实时刷新的交易界面，显示账户信息、持仓情况和订单状态。
支持命令行输入进行交易操作。
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.prompt import Prompt
    from rich.columns import Columns
    from rich.layout import Layout
    from rich.align import Align
    import requests
except ImportError:
    print("❌ 需要安装 rich 库: pip install rich")
    sys.exit(1)


class TradingTerminal:
    """交易终端 - 实时交易界面"""

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

        # 数据存储
        self.account_info = {}
        self.positions = []
        self.orders = []
        self.trades = []

        # 控制标志
        self.running = True
        self.last_update = datetime.now()

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
                    self.console.print("⚠️ 未发现交易工具，请确保服务器启用了 --enable-trade 参数", style="yellow")
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

    def update_data(self):
        """更新所有数据"""
        try:
            # 获取账户持仓
            positions_data = self._make_request("get_account_positions", {})
            if positions_data and "error" not in positions_data:
                self.account_info = {
                    'account_id': positions_data.get('account_id', 'N/A'),
                    'cash': positions_data.get('cash', 0),
                    'frozen_cash': positions_data.get('frozen_cash', 0),
                    'market_value': positions_data.get('market_value', 0),
                    'total_asset': positions_data.get('total_asset', 0)
                }
                self.positions = positions_data.get('positions', [])
            else:
                self.account_info = {}
                self.positions = []

            # 获取订单信息
            orders_data = self._make_request("query_orders", {})
            if orders_data and "error" not in orders_data:
                self.orders = orders_data.get('orders', [])
                self.trades = orders_data.get('trades', [])
            else:
                self.orders = []
                self.trades = []

            self.last_update = datetime.now()

        except Exception as e:
            self.console.print(f"❌ 更新数据失败: {e}", style="red")

    def create_account_panel(self) -> Panel:
        """创建账户信息面板"""
        if not self.account_info:
            return Panel("无法获取账户信息", title="账户信息", border_style="red")

        info_text = "\n".join([
            f"账户ID: {self.account_info.get('account_id', 'N/A')}",
            f"可用资金: ¥{self.account_info.get('cash', 0):,.2f}",
            f"冻结资金: ¥{self.account_info.get('frozen_cash', 0):,.2f}",
            f"持仓市值: ¥{self.account_info.get('market_value', 0):,.2f}",
            f"总资产: ¥{self.account_info.get('total_asset', 0):,.2f}",
            f"最后更新: {self.last_update.strftime('%H:%M:%S')}"
        ])

        return Panel(info_text, title="📊 账户信息", border_style="blue")

    def create_positions_panel(self) -> Panel:
        """创建持仓信息面板"""
        if not self.positions:
            return Panel("暂无持仓", title="📈 持仓情况", border_style="yellow")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("股票代码", style="cyan", min_width=10)
        table.add_column("持仓量", justify="right", style="green", min_width=8)
        table.add_column("可用量", justify="right", style="green", min_width=8)
        table.add_column("成本价", justify="right", style="yellow", min_width=8)
        table.add_column("当前价", justify="right", style="white", min_width=8)
        table.add_column("盈亏比", justify="right", style="red", min_width=8)
        table.add_column("盈亏额", justify="right", style="red", min_width=10)

        # 获取当前价格（这里简化处理，实际应该从实时数据获取）
        # 为了演示，我们使用成本价作为当前价
        for position in self.positions:
            code = position.get('code', '')
            volume = position.get('volume', 0)
            can_use_volume = position.get('can_use_volume', 0)
            avg_price = position.get('avg_price', 0)

            # 模拟当前价格（实际应用中应该从实时数据获取）
            current_price = avg_price  # 这里用成本价代替
            profit_ratio = 0.0 if avg_price == 0 else (current_price - avg_price) / avg_price * 100
            profit_amount = (current_price - avg_price) * volume

            table.add_row(
                code,
                f"{volume:,}",
                f"{can_use_volume:,}",
                f"¥{avg_price:.2f}",
                f"¥{current_price:.2f}",
                f"{profit_ratio:+.2f}%",
                f"¥{profit_amount:+,.2f}"
            )

            # 添加该股票的订单信息
            stock_orders = [order for order in self.orders if order.get('code') == code]
            if stock_orders:
                for order in stock_orders:
                    # 检查订单是否过期（超过120秒的已完成订单不显示）
                    order_status = order.get('order_status', '')
                    if order_status in ['已成', '已撤', '废单']:
                        order_time_str = order.get('order_time', '')
                        if order_time_str:
                            try:
                                if isinstance(order_time_str, str):
                                    order_time = datetime.fromisoformat(order_time_str.replace('Z', '+00:00'))
                                else:
                                    order_time = order_time_str

                                if datetime.now() - order_time > timedelta(seconds=120):
                                    continue  # 跳过过期订单
                            except:
                                pass  # 时间解析失败，继续显示

                    order_id = order.get('order_id', 0)
                    order_type = order.get('order_type', '')
                    order_volume = order.get('volume', 0)
                    order_price = order.get('price', 0)
                    status = order.get('order_status', '')

                    table.add_row(
                        f"  └─ 订单 {order_id}",
                        f"{order_type} {order_volume}",
                        "",
                        f"¥{order_price:.2f}",
                        "",
                        status,
                        ""
                    )

        return Panel(table, title="📈 持仓情况", border_style="green")

    def create_command_panel(self) -> Panel:
        """创建命令输入面板"""
        commands = [
            "buy CODE VOLUME [PRICE]    - 买入委托 (限价/市价)",
            "sell CODE VOLUME [PRICE]   - 卖出委托 (限价/市价)",
            "cancel ORDER_ID            - 撤单",
            "refresh                    - 手动刷新数据",
            "quit                       - 退出程序"
        ]

        command_text = "\n".join([f"• {cmd}" for cmd in commands])

        return Panel(
            f"[bold cyan]支持的命令:[/bold cyan]\n{command_text}\n\n[dim]输入命令后按回车执行...[/dim]",
            title="💬 命令输入",
            border_style="cyan"
        )

    def create_layout(self) -> Layout:
        """创建界面布局"""
        layout = Layout()

        # 创建垂直布局
        layout.split_column(
            Layout(name="account", size=8),
            Layout(name="positions"),
            Layout(name="commands", size=12)
        )

        # 填充内容
        layout["account"].update(self.create_account_panel())
        layout["positions"].update(self.create_positions_panel())
        layout["commands"].update(self.create_command_panel())

        return layout

    def execute_command(self, command: str) -> bool:
        """执行用户命令

        Returns:
            bool: 是否继续运行程序
        """
        command = command.strip()
        if not command:
            return True

        try:
            if command.lower() == 'quit':
                return False
            elif command.lower() == 'refresh':
                self.console.print("[bold green]🔄 手动刷新数据...[/bold green]")
                self.update_data()
            elif command.startswith('buy '):
                # 格式: buy CODE VOLUME [PRICE]
                parts = command[4:].strip().split()
                if len(parts) < 2:
                    self.console.print("[red]❌ 用法: buy CODE VOLUME [PRICE][/red]")
                    return True

                code = parts[0]
                try:
                    volume = int(parts[1])
                    price = float(parts[2]) if len(parts) > 2 else None
                except ValueError:
                    self.console.print("[red]❌ 数量和价格必须是数字[/red]")
                    return True

                price_type = "limit" if price else "market"
                result = self._make_request("place_order", {
                    "code": code,
                    "order_type": "buy",
                    "volume": volume,
                    "price": price,
                    "price_type": price_type
                })

                if result and "error" not in result:
                    self.console.print(f"[green]✅ 买入委托已提交: {code} {volume}股 @ {price if price else '市价'}[/green]")
                    self.update_data()  # 立即刷新数据
                else:
                    self.console.print("[red]❌ 买入委托失败[/red]")

            elif command.startswith('sell '):
                # 格式: sell CODE VOLUME [PRICE]
                parts = command[5:].strip().split()
                if len(parts) < 2:
                    self.console.print("[red]❌ 用法: sell CODE VOLUME [PRICE][/red]")
                    return True

                code = parts[0]
                try:
                    volume = int(parts[1])
                    price = float(parts[2]) if len(parts) > 2 else None
                except ValueError:
                    self.console.print("[red]❌ 数量和价格必须是数字[/red]")
                    return True

                price_type = "limit" if price else "market"
                result = self._make_request("place_order", {
                    "code": code,
                    "order_type": "sell",
                    "volume": volume,
                    "price": price,
                    "price_type": price_type
                })

                if result and "error" not in result:
                    self.console.print(f"[green]✅ 卖出委托已提交: {code} {volume}股 @ {price if price else '市价'}[/green]")
                    self.update_data()  # 立即刷新数据
                else:
                    self.console.print("[red]❌ 卖出委托失败[/red]")

            elif command.startswith('cancel '):
                # 格式: cancel ORDER_ID
                try:
                    order_id = int(command[7:].strip())
                except ValueError:
                    self.console.print("[red]❌ 用法: cancel ORDER_ID (ORDER_ID必须是数字)[/red]")
                    return True

                result = self._make_request("cancel_order", {"order_id": order_id})

                if result and "error" not in result:
                    self.console.print(f"[green]✅ 撤单请求已提交: {order_id}[/green]")
                    self.update_data()  # 立即刷新数据
                else:
                    self.console.print("[red]❌ 撤单失败[/red]")

            else:
                self.console.print(f"[yellow]❓ 未知命令: {command}[/yellow]")
                self.console.print("[dim]输入 'help' 查看帮助[/dim]")

        except Exception as e:
            self.console.print(f"[red]❌ 命令执行出错: {e}[/red]")

        return True

    def run(self):
        """运行交易终端"""
        self.console.clear()

        # 初始化数据
        self.console.print("[bold blue]🚀 启动交易终端...[/bold blue]")
        self.update_data()

        # 创建实时显示界面
        with Live(self.create_layout(), refresh_per_second=1, screen=True) as live:
            # 启动自动刷新线程
            def auto_refresh():
                while self.running:
                    time.sleep(3)  # 每3秒刷新一次
                    if self.running:
                        self.update_data()
                        live.update(self.create_layout())

            refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
            refresh_thread.start()

            try:
                while self.running:
                    # 显示界面并等待用户输入
                    live.update(self.create_layout())

                    # 获取用户输入
                    try:
                        command = self.console.input("\n[bold cyan]交易命令 > [/bold cyan]").strip()
                        if not self.execute_command(command):
                            break
                    except KeyboardInterrupt:
                        break
                    except EOFError:
                        break

            except KeyboardInterrupt:
                pass
            finally:
                self.running = False
                self.console.print("\n[bold yellow]👋 交易终端已退出[/bold yellow]")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='交易终端 - 实时交易界面')
    parser.add_argument('--server-url', type=str,
                       default='http://localhost:9696',
                       help='MCP服务器URL')
    parser.add_argument('--api-key', type=str,
                       help='API密钥，用于认证。如果不提供则尝试从环境变量读取')

    args = parser.parse_args()

    # 获取API密钥
    api_key = args.api_key
    if not api_key:
        api_key = os.environ.get('XTDATA_MCP_API_KEY')

    print("=== 交易终端 ===")
    print(f"服务器URL: {args.server_url}")
    print(f"API密钥: {'已设置' if api_key else '未设置'}")
    print("-" * 40)
    print("正在启动实时交易界面...")
    print("按 Ctrl+C 退出程序")
    print()

    # 创建并运行交易终端
    terminal = TradingTerminal(args.server_url, api_key)
    terminal.run()


if __name__ == "__main__":
    main()