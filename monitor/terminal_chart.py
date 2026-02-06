#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终端实时股票价格曲线显示工具

使用 plotext 库在终端中绘制股票实时价格曲线
从 real_time_monitor.py 产生的 SQLite 数据库读取数据
支持实时刷新显示
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import plotext as plt
except ImportError:
    print("错误: 需要安装 plotext 库")
    print("请运行: pip install plotext")
    sys.exit(1)

from monitor.real_time_sqlite import RealTimeMonitorSQLite


class TerminalStockChart:
    """终端股票图表显示器"""

    def __init__(self, db_path: str = None):
        """
        初始化图表显示器

        Args:
            db_path: SQLite数据库路径，默认使用标准路径
        """
        if db_path is None:
            db_path = "/tmp/cache_output/quantara/monitor/real_time_monitor/real_time_monitor.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            print(f"错误: 数据库文件不存在: {self.db_path}")
            print("请先运行 real_time_monitor.py 生成数据")
            sys.exit(1)
        
        self.sqlite_storage = RealTimeMonitorSQLite(self.db_path)

    def get_stock_data(self, code: str, limit: int = 100):
        """
        获取指定股票的历史价格数据

        Args:
            code: 股票代码
            limit: 最多获取的数据点数量

        Returns:
            (timestamps, prices) 元组
        """
        # 查询数据，按时间升序排列
        records = self.sqlite_storage.query_by_code(
            code=code,
            limit=limit,
            ascending=False
        )

        if not records:
            return [], []

        timestamps = []
        prices = []

        for record in records:
            ts_str = record.get('ts')
            price = record.get('current_price')

            if ts_str and price is not None:
                # 解析时间戳，只保留时分秒用于显示
                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    timestamps.append(dt.strftime("%H:%M:%S"))
                except ValueError:
                    timestamps.append(ts_str)
                prices.append(float(price))

        return timestamps, prices

    def get_available_codes(self):
        """获取数据库中所有可用的股票代码"""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT code FROM real_time_indicators ORDER BY code")
            codes = [row[0] for row in cur.fetchall()]
        return codes

    def draw_chart(self, code: str, limit: int = 100, width: int = None, height: int = None):
        """
        绘制股票价格曲线

        Args:
            code: 股票代码
            limit: 最多显示的数据点数量
            width: 图表宽度（字符数），None为自动
            height: 图表高度（字符数），None为自动
        """
        timestamps, prices = self.get_stock_data(code, limit)

        if not prices:
            plt.clear_figure()
            plt.title(f"股票 {code} - 无数据")
            plt.show()
            return False

        # 清除之前的图形
        plt.clear_figure()

        # 设置图表大小
        # 如果未指定，默认使用终端的1/3大小
        if width is None or height is None:
            term_width, term_height = plt.terminal_size()
            width = width or max(60, term_width // 3)
            height = height or max(15, term_height // 3)
        
        plt.plotsize(width, height)

        # 绘制价格曲线
        plt.plot(prices, marker="braille", label="当前价格")

        # 设置标题和标签
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        latest_price = prices[-1] if prices else 0
        price_change = 0
        if len(prices) >= 2:
            price_change = (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] != 0 else 0

        plt.title(f"股票 {code} 实时价格曲线 | 最新: {latest_price:.2f} | 变化: {price_change:+.2f}%")
        plt.xlabel(f"数据点 (共 {len(prices)} 个) | 更新时间: {current_time}")
        plt.ylabel("价格")

        # 设置x轴标签（间隔显示时间戳，避免拥挤）
        if timestamps:
            num_labels = min(10, len(timestamps))
            if num_labels > 1:
                step = len(timestamps) // (num_labels - 1)
                x_ticks = list(range(0, len(timestamps), step))
                x_labels = [timestamps[i] for i in x_ticks if i < len(timestamps)]
                if x_ticks and x_labels:
                    plt.xticks(x_ticks, x_labels)

        # 添加网格
        plt.grid(True, True)

        # 设置颜色主题
        plt.theme("pro")

        # 显示图表
        plt.show()

        return True

    def run_realtime(self, code: str, interval: int = 3, limit: int = 100, 
                     width: int = None, height: int = None):
        """
        实时刷新显示股票价格曲线

        Args:
            code: 股票代码
            interval: 刷新间隔（秒）
            limit: 最多显示的数据点数量
            width: 图表宽度（字符数）
            height: 图表高度（字符数）
        """
        print(f"开始实时监控股票 {code}，每 {interval} 秒刷新一次")
        print("按 Ctrl+C 退出")
        print()

        try:
            while True:
                # 清屏并绘制
                plt.clear_terminal()
                has_data = self.draw_chart(code, limit, width, height)

                if not has_data:
                    print(f"\n提示: 股票 {code} 暂无数据，等待数据更新...")
                    available = self.get_available_codes()
                    if available:
                        print(f"可用的股票代码: {', '.join(available[:20])}")
                        if len(available) > 20:
                            print(f"... 共 {len(available)} 个")

                # 等待下次刷新
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n已退出实时监控")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='终端实时股票价格曲线显示工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python terminal_chart.py --code 000001.SZ                    # 显示实时曲线(默认1/3终端大小)
  python terminal_chart.py --code 000001.SZ --interval 5       # 每5秒刷新一次
  python terminal_chart.py --code 000001.SZ --limit 50         # 只显示最近50个数据点
  python terminal_chart.py --code 000001.SZ -W 80 -H 20        # 指定图表宽80字符、高20行
  python terminal_chart.py --list                              # 列出所有可用的股票代码
        """
    )

    parser.add_argument(
        '--code', '-c',
        type=str,
        help='股票代码，如 000001.SZ'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=3,
        help='刷新间隔（秒），默认3秒'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=100,
        help='最多显示的数据点数量，默认100'
    )
    parser.add_argument(
        '--width', '-W',
        type=int,
        default=None,
        help='图表宽度（字符数），默认为终端宽度的1/3'
    )
    parser.add_argument(
        '--height', '-H',
        type=int,
        default=None,
        help='图表高度（字符数），默认为终端高度的1/3'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='SQLite数据库路径（可选）'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出数据库中所有可用的股票代码'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='只显示一次，不实时刷新'
    )

    args = parser.parse_args()

    # 创建图表显示器
    chart = TerminalStockChart(db_path=args.db_path)

    # 列出可用代码
    if args.list:
        codes = chart.get_available_codes()
        if codes:
            print(f"数据库中共有 {len(codes)} 个股票代码:")
            for i, code in enumerate(codes, 1):
                print(f"  {i:3d}. {code}")
        else:
            print("数据库中暂无数据")
        return

    # 检查是否提供了股票代码
    if not args.code:
        parser.print_help()
        print("\n错误: 请提供股票代码 (--code)")
        
        # 提示可用的代码
        codes = chart.get_available_codes()
        if codes:
            print(f"\n可用的股票代码示例: {', '.join(codes[:5])}")
        return

    # 显示图表
    if args.once:
        # 单次显示
        chart.draw_chart(args.code, args.limit, args.width, args.height)
    else:
        # 实时刷新
        chart.run_realtime(args.code, args.interval, args.limit, args.width, args.height)


if __name__ == '__main__':
    main()
