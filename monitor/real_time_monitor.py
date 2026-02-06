#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日股票监控 - 实时行情监控和分析脚本
监控盘中实时行情，计算关键指标并保存到本地
"""

import os
import sys
import time
import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging
from prettytable import PrettyTable

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
print(f"项目根目录已添加到Python路径: {project_root}")
print(f"Python路径包含: {[p for p in sys.path if 'quantara' in p or 'prediction' in p]}")

# 导入自定义模块
try:
    from common.logger import init_logger, logger
    from common.utils import load_data
    from common.data_getter import DataGetter
    from monitor.real_time_sqlite import RealTimeMonitorSQLite
    from monitor.stock_data_provider import StockDataProvider, StockData
    print("✓ 成功导入所有模块")
except ImportError as e:
    print(f"✗ 模块导入失败: {e}")
    import sys
    sys.exit(1)

# 初始化日志
log_dir = '/tmp/cache_output/quantara/logs'
init_logger('real_time_monitor', log_dir)


class RealTimeStockMonitor:
    """实时股票监控器"""

    # 数据加载模式
    DATA_MODE_FILE = 'file'      # 从文件加载
    DATA_MODE_ONLINE = 'online'  # 在线获取

    def __init__(self, data_mode: str = DATA_MODE_FILE):
        """
        初始化监控器

        Args:
            data_mode: 数据加载模式，'file' 或 'online'
        """
        self.cache_dir = Path("/tmp/cache_output/quantara/monitor/real_time_monitor")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 数据模式
        self.data_mode = data_mode

        # 数据存储
        self.data_getter = DataGetter()
        self.stock_data_provider: StockDataProvider = None  # 延迟初始化

        # SQLite 存储（数据库文件与pkl在同一目录）
        self.sqlite_db_path = self.cache_dir / "real_time_monitor.db"
        self.sqlite_storage = RealTimeMonitorSQLite(self.sqlite_db_path)

        # 监控配置
        self.monitor_interval = 10  # 监控间隔（秒）
        self.max_retries = 3  # 最大重试次数

        # 默认数据文件路径（文件模式使用）
        self.default_data_file = Path("/tmp/cache_output/stock/update_stock_advanced_features.pkl")

    def load_offline_data(self, stock_codes: list = None):
        """
        加载数据

        支持两种模式：
        - 文件模式 (file)：从指定路径读取pkl文件
        - 在线模式 (online)：通过DataGetter获取历史行情和基本信息

        Args:
            stock_codes: 股票代码列表，在线模式必须提供，文件模式可选（用于过滤）

        Returns:
            是否加载成功
        """
        try:
            logger.info(f"开始加载数据，模式: {self.data_mode}...")

            if self.data_mode == self.DATA_MODE_FILE:
                # 文件模式
                if not self.default_data_file.exists():
                    logger.error(f"数据文件不存在: {self.default_data_file}")
                    return False

                self.stock_data_provider = StockDataProvider(
                    mode=StockDataProvider.MODE_FILE,
                    file_path=self.default_data_file,
                )
                success = self.stock_data_provider.load_data(stock_codes)

            else:
                # 在线模式
                if not stock_codes:
                    logger.error("在线模式必须提供股票代码列表")
                    return False

                self.stock_data_provider = StockDataProvider(
                    mode=StockDataProvider.MODE_ONLINE,
                    data_getter=self.data_getter,
                    history_count=100,
                )
                success = self.stock_data_provider.load_data(stock_codes)

            if success:
                logger.info(f"成功加载 {len(self.stock_data_provider.get_all_codes())} 只股票的数据")
            else:
                logger.warning("数据加载失败或为空")

            return success

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            import traceback
            logger.debug(f"加载数据失败详情: {traceback.format_exc()}")
            return False

    def get_stock_list_from_file(self, stock_codes_file: str) -> list:
        """
        从文件读取股票代码列表

        Args:
            stock_codes_file: 股票代码文件路径

        Returns:
            股票代码列表
        """
        file_stock_codes = []
        if stock_codes_file:
            if not os.path.exists(stock_codes_file):
                logger.error(f"股票代码文件不存在: {stock_codes_file}")
                return []

            try:
                with open(stock_codes_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        code = line.strip()
                        if code:  # 跳过空行
                            file_stock_codes.append(code)
                logger.info(f"从文件 {stock_codes_file} 读取到 {len(file_stock_codes)} 个股票代码")
            except Exception as e:
                logger.error(f"读取股票代码文件失败 {stock_codes_file}: {e}")
                return []

        return list(set(file_stock_codes))

    def get_stock_list(self, stock_codes_file=None):
        """获取需要监控的股票列表

        Args:
            stock_codes_file: 股票代码文件路径，如果提供则优先从文件读取

        Returns:
            需要监控的股票代码列表
        """
        try:
            # 优先从文件读取股票代码
            file_stock_codes = self.get_stock_list_from_file(stock_codes_file)

            # 从数据提供者中提取所有可用的股票代码
            available_stock_codes = set()
            if self.stock_data_provider is not None:
                available_stock_codes = set(self.stock_data_provider.get_all_codes())

            # 确定最终的股票代码列表
            if file_stock_codes:
                if available_stock_codes:
                    # 如果有数据提供者，取文件代码和可用代码的交集
                    final_stock_codes = [code for code in file_stock_codes if code in available_stock_codes]
                    logger.info(f"文件指定 {len(file_stock_codes)} 个代码，已加载 {len(available_stock_codes)} 个代码")
                    logger.info(f"交集得到 {len(final_stock_codes)} 个有效股票代码")

                    if len(final_stock_codes) == 0:
                        logger.warning("文件指定的股票代码与已加载数据完全没有交集，使用文件中的代码")
                        final_stock_codes = file_stock_codes
                else:
                    # 没有数据提供者，直接使用文件中的代码
                    final_stock_codes = file_stock_codes
                    logger.info(f"使用文件中的 {len(final_stock_codes)} 个股票代码")
            else:
                # 如果没有文件指定，使用所有可用的股票代码
                final_stock_codes = list(available_stock_codes)
                logger.info(f"使用所有已加载的 {len(final_stock_codes)} 个股票代码")

            if not final_stock_codes:
                logger.error("没有有效的股票代码可以监控")
                sys.exit(1)

            logger.info(f"最终监控 {len(final_stock_codes)} 只股票")
            return final_stock_codes

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            sys.exit(1)

    def calculate_indicators(self, stock_codes, real_time_data):
        """计算关键指标"""
        logger.info("开始计算关键指标...")

        indicators_data = []

        for stock_code in stock_codes:
            try:
                indicator = self._calculate_single_stock_indicator(stock_code, real_time_data.get(stock_code))
                if indicator:
                    indicators_data.append(indicator)
            except Exception as e:
                logger.warning(f"计算股票 {stock_code} 指标失败: {e}")
                continue

        logger.info(f"成功计算 {len(indicators_data)} 只股票的指标")
        return indicators_data

    def _calculate_single_stock_indicator(self, stock_code, real_time_tick):
        """
        计算单个股票的关键指标

        注意：调用方需确保 real_time_tick 为有效数据，本方法不做有效性检查
        """
        try:
            # 从 StockDataProvider 获取数据
            stock_data_obj: StockData = None
            if self.stock_data_provider is not None:
                stock_data_obj = self.stock_data_provider.get_stock_data(stock_code)

            # 获取历史数据、名称、前一日收盘价
            stock_data = None  # 历史行情 DataFrame
            stock_name = ''    # 股票名称，默认空字符串
            prev_close = None  # 前一日收盘价

            if stock_data_obj is not None:
                stock_name = stock_data_obj.get_name(default='')
                prev_close = stock_data_obj.prev_close
                stock_data = stock_data_obj.history_df

            # 解析实时数据（假设数据有效，不做有效性检查）
            if isinstance(real_time_tick, pd.DataFrame):
                latest_rt = real_time_tick.iloc[-1]
                rt_current_price = latest_rt.get('close')
                rt_open_price = latest_rt.get('open')
                rt_high_price = latest_rt.get('high')
                rt_low_price = latest_rt.get('low')
                rt_volume = latest_rt.get('volume', 0.0)
                rt_pre_close = latest_rt.get('pre_close')
            else:
                # 字典格式
                rt_current_price = real_time_tick.get('close')
                rt_open_price = real_time_tick.get('open')
                rt_high_price = real_time_tick.get('high')
                rt_low_price = real_time_tick.get('low')
                rt_volume = real_time_tick.get('volume', 0.0)
                rt_pre_close = real_time_tick.get('pre_close')

            # 如果没有 prev_close，使用实时数据的 pre_close
            if prev_close is None or prev_close <= 0:
                if rt_pre_close is not None and rt_pre_close > 0:
                    prev_close = rt_pre_close

            # 计算前五日涨跌幅和前五日平均成交量
            prev_5_change = 0.0
            prev_5_volumes = 0.0
            prev_day_change = 0.0

            if stock_data is not None and isinstance(stock_data, pd.DataFrame) and not stock_data.empty:
                if len(stock_data) >= 6:
                    prev_5_close = stock_data.iloc[-6]['close']
                    if prev_5_close != 0:
                        prev_5_change = (prev_close - prev_5_close) / prev_5_close * 100

                if len(stock_data) >= 5:
                    prev_5_volumes = stock_data.iloc[-5:]['volume'].mean()

                if len(stock_data) >= 2:
                    prev_day_close = stock_data.iloc[-2]['close']
                    if prev_day_close != 0:
                        prev_day_change = (prev_close - prev_day_close) / prev_day_close * 100

            # 处理实时数据，确定当前价格等
            current_price = rt_current_price if rt_current_price and rt_current_price > 0 else prev_close
            open_price = rt_open_price if rt_open_price and rt_open_price > 0 else current_price
            high_price = rt_high_price if rt_high_price and rt_high_price > 0 else current_price
            low_price = rt_low_price if rt_low_price and rt_low_price > 0 else current_price
            current_volume = rt_volume if rt_volume else 0.0

            # 计算各项指标
            open_change = (open_price - prev_close) / prev_close * 100 if prev_close != 0 else 0.0
            high_change = (high_price - prev_close) / prev_close * 100 if prev_close != 0 else 0.0
            low_change = (low_price - prev_close) / prev_close * 100 if prev_close != 0 else 0.0
            current_change = (current_price - prev_close) / prev_close * 100 if prev_close != 0 else 0.0

            # 量比计算
            volume_ratio = current_volume / prev_5_volumes if prev_5_volumes > 0 else 0.0

            # 数据验证和清理
            try:
                current_volume_int = max(0, int(current_volume)) if current_volume != -1 else 0
                prev_5_volumes_int = max(0, int(prev_5_volumes)) if prev_5_volumes != -1 else 0
            except (ValueError, TypeError):
                current_volume_int = 0
                prev_5_volumes_int = 0

            return {
                '股票代码': stock_code,
                '股票名称': stock_name,
                '当前涨跌幅': round(current_change, 2),
                '量比': round(volume_ratio, 2),
                '前五日涨跌幅': round(prev_5_change, 2),
                '上一日涨跌幅': round(prev_day_change, 2),
                '当日开盘涨跌幅': round(open_change, 2),
                '当日最高涨跌幅': round(high_change, 2),
                '当日最低涨跌幅': round(low_change, 2),
                '当日成交量': current_volume_int,
                '前五日平均量': prev_5_volumes_int,
                # 价格字段（用于SQLite存储）
                '当前价格': float(current_price),
                '当日最高价': float(high_price),
                '当日最低价': float(low_price),
            }

        except Exception as e:
            logger.error(f"计算股票 {stock_code} 指标失败: {e}")
            import traceback
            logger.debug(f"完整错误堆栈: {traceback.format_exc()}")
            return None

    def evaluate_monitoring_results(self, indicators_data):
        """评估监控结果，用prettytable表格形式展现"""
        try:
            if not indicators_data:
                return

            warning_threshold = 3.0  # 涨跌幅阈值 3%
            warnings = []

            print(f"\n=== 监控结果 ({datetime.now().strftime('%H:%M:%S')}) ===")

            # 创建PrettyTable
            table = PrettyTable()

            # 设置列名
            table.field_names = ['状态', '股票代码', '当前涨跌幅', '量比', '前五日涨跌幅', '上一日涨跌幅',
                                '当日开盘涨跌幅', '当日最高涨跌幅', '当日最低涨跌幅', '当日成交量', '前五日平均量']

            # 设置表格样式
            table.align = 'c'  # 居中对齐
            table.border = True
            table.header = True
            table.header_style = 'upper'

            # 添加数据行
            for indicator in indicators_data:
                stock_code = indicator.get('股票代码', '未知')
                current_change = indicator.get('当前涨跌幅', 0.0)
                volume_ratio = indicator.get('量比', 0.0)
                prev_5_change = indicator.get('前五日涨跌幅', 0.0)
                prev_day_change = indicator.get('上一日涨跌幅', 0.0)
                open_change = indicator.get('当日开盘涨跌幅', 0.0)
                high_change = indicator.get('当日最高涨跌幅', 0.0)
                low_change = indicator.get('当日最低涨跌幅', 0.0)
                current_volume = indicator.get('当日成交量', 0)
                prev_5_volumes = indicator.get('前五日平均量', 0)

                # 确定状态
                status = "⚠️" if abs(current_change) >= warning_threshold else "✓"
                if abs(current_change) >= warning_threshold:
                    warning_msg = f"股票 {stock_code} 当前涨跌幅 {current_change:.2f}%"
                    warnings.append(warning_msg)

                # 添加行数据
                table.add_row([
                    status,
                    stock_code,
                    f"{current_change:.2f}%",
                    f"{volume_ratio:.2f}",
                    f"{prev_5_change:.2f}%",
                    f"{prev_day_change:.2f}%",
                    f"{open_change:.2f}%",
                    f"{high_change:.2f}%",
                    f"{low_change:.2f}%",
                    f"{current_volume:,}",
                    f"{prev_5_volumes:,}"
                ])

            # 打印表格
            print(table)

            print(f"\n=== 本次监控 {len(indicators_data)} 只股票，异常 {len(warnings)} 只 ===")

            # 记录到日志
            if warnings:
                logger.warning(f"本次监控发现 {len(warnings)} 只股票出现异常涨跌幅")
                for warning in warnings:
                    logger.warning(warning)
            else:
                logger.info("本次监控未发现异常涨跌幅")

        except Exception as e:
            logger.error(f"评估监控结果失败: {e}")
            import traceback
            logger.debug(f"评估监控结果失败详情: {traceback.format_exc()}")

    def save_real_time_data(self, indicators_data, save_csv=True):
        """
        保存实时数据到本地

        说明：
        - 保留原有pkl/CSV方案（向后兼容），但实时监控流程默认只写入SQLite
        - 当前RealTimeStockMonitor内部已不再调用该方法，主要用于手动导出
        """
        try:
            if not indicators_data:
                logger.warning("没有数据需要保存")
                return

            # 创建DataFrame
            df = pd.DataFrame(indicators_data)

            # 生成文件名（使用当前时间）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.pkl"
            file_path = self.cache_dir / filename

            # 保存为pickle格式
            with open(file_path, 'wb') as f:
                pickle.dump(df, f)

            logger.info(f"实时数据已保存到: {file_path}")
            logger.info(f"数据包含 {len(df)} 只股票的实时指标")

            # 同时保存为CSV格式（可选，便于查看）
            if save_csv:
                csv_path = file_path.with_suffix('.csv')
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                logger.info(f"CSV格式数据已保存到: {csv_path}")

            return str(file_path)

        except Exception as e:
            logger.error(f"保存实时数据失败: {e}")
            logger.debug(f"保存数据失败详情: 数据长度={len(indicators_data) if indicators_data else 0}，数据类型={type(indicators_data)}")
            return None

    def is_trading_time(self):
        """检查当前是否为A股交易时间"""
        now = datetime.now()
        current_time = now.time()

        # A股交易时间：09:30-11:30 和 13:00-15:00
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()

        # 检查是否为工作日（周一到周五）
        is_weekday = now.weekday() < 5  # 0-4 代表周一到周五

        # 检查是否在交易时间范围内
        is_morning_trading = morning_start <= current_time <= morning_end
        is_afternoon_trading = afternoon_start <= current_time <= afternoon_end

        return is_weekday and (is_morning_trading or is_afternoon_trading)

    def run_monitoring(self, duration_minutes=60, stock_codes_file=None):
        """运行监控程序"""
        try:
            logger.info("开始实时股票监控...")
            logger.info(f"监控时长: {duration_minutes} 分钟")
            logger.info(f"监控间隔: {self.monitor_interval} 秒")
            logger.info(f"数据模式: {self.data_mode}")

            # 先从文件获取股票代码列表（用于在线模式）
            file_stock_codes = self.get_stock_list_from_file(stock_codes_file)

            # 加载数据（在线模式需要传入股票代码列表）
            load_codes = file_stock_codes if self.data_mode == self.DATA_MODE_ONLINE else None
            if not self.load_offline_data(load_codes):
                logger.error("加载数据失败，退出监控")
                return

            # 获取最终的股票列表
            stock_codes = self.get_stock_list(stock_codes_file)
            if not stock_codes:
                logger.error("获取股票列表失败，退出监控")
                return

            # 计算监控次数
            total_iterations = (duration_minutes * 60) // self.monitor_interval

            for iteration in range(total_iterations):
                try:
                    logger.info(f"开始第 {iteration + 1}/{total_iterations} 次监控...")

                    # 检查是否超过交易结束时间（15:10）
                    current_time = datetime.now().time()
                    trading_end_extended = datetime.strptime("15:10", "%H:%M").time()
                    if current_time > trading_end_extended:
                        logger.info(f"当前时间已超过15:10，结束今日监控")
                        print(f"🏁 当前时间已超过15:10，结束今日监控")
                        break

                    # 检查是否为交易时间
                    if not self.is_trading_time():
                        current_time_str = datetime.now().strftime("%H:%M:%S")
                        logger.info(f"当前时间 {current_time_str} 不在A股交易时间内，跳过本次监控")
                        print(f"⏰ 当前时间 {current_time_str} 不在A股交易时间内，跳过监控")

                        # 等待下次监控
                        if iteration < total_iterations - 1:
                            logger.info(f"等待 {self.monitor_interval} 秒后进行下次检查...")
                            time.sleep(self.monitor_interval)
                        continue

                    # 获取实时数据
                    real_time_data = self.data_getter.get_real_time_data(stock_codes)

                    # 检查实时数据有效性，无效则跳过本次监控
                    if real_time_data is None:
                        logger.warning(f"第 {iteration + 1} 次监控获取实时数据失败，跳过")
                        if iteration < total_iterations - 1:
                            time.sleep(self.monitor_interval)
                        continue

                    # 计算指标
                    indicators_data = self.calculate_indicators(stock_codes, real_time_data)

                    # 评估监控结果
                    if indicators_data:
                        self.evaluate_monitoring_results(indicators_data)

                    # 保存数据：仅写入SQLite，不再保存pkl/CSV
                    if indicators_data:
                        try:
                            inserted = self.sqlite_storage.insert_batch(
                                indicators_data,
                                ts=datetime.now(),
                            )
                            logger.info(f"第 {iteration + 1} 次监控完成，SQLite 已写入 {inserted} 行")
                        except Exception as e:
                            logger.error(f"写入SQLite失败: {e}")

                    # 等待下次监控
                    if iteration < total_iterations - 1:
                        logger.info(f"等待 {self.monitor_interval} 秒后进行下次监控...")
                        time.sleep(self.monitor_interval)

                except Exception as e:
                    logger.error(f"第 {iteration + 1} 次监控失败: {e}")
                    logger.debug(f"第 {iteration + 1} 次监控失败详情: {type(e).__name__}")
                    continue

            logger.info("实时股票监控完成")

        except KeyboardInterrupt:
            logger.info("监控程序被用户中断")
        except Exception as e:
            logger.error(f"监控程序异常退出: {e}")
            import traceback
            logger.debug(f"监控程序异常退出详情: {traceback.format_exc()}")

    def run_once(self, stock_codes_file=None, check_trading_time=True):
        """执行一次监控"""
        try:
            logger.info("执行单次实时股票监控...")
            logger.info(f"数据模式: {self.data_mode}")

            # 检查是否为交易时间（可选择性检查）
            if check_trading_time and not self.is_trading_time():
                current_time = datetime.now().strftime("%H:%M:%S")
                logger.warning(f"当前时间 {current_time} 不在A股交易时间内，无法执行监控")
                print(f"⏰ 当前时间 {current_time} 不在A股交易时间内，无法执行监控")
                return None

            # 先从文件获取股票代码列表（用于在线模式）
            file_stock_codes = self.get_stock_list_from_file(stock_codes_file)

            # 加载数据（在线模式需要传入股票代码列表）
            load_codes = file_stock_codes if self.data_mode == self.DATA_MODE_ONLINE else None
            if not self.load_offline_data(load_codes):
                logger.error("加载数据失败")
                return

            # 获取最终的股票列表
            stock_codes = self.get_stock_list(stock_codes_file)
            if not stock_codes:
                logger.error("获取股票列表失败")
                return

            # 获取实时数据
            real_time_data = self.data_getter.get_real_time_data(stock_codes)

            # 检查实时数据有效性
            if real_time_data is None:
                logger.error("获取实时数据失败")
                return None

            # 计算指标
            indicators_data = self.calculate_indicators(stock_codes, real_time_data)

            # 评估监控结果
            if indicators_data:
                self.evaluate_monitoring_results(indicators_data)

            # 保存数据：单次模式同样只写入SQLite
            if indicators_data:
                try:
                    inserted = self.sqlite_storage.insert_batch(
                        indicators_data,
                        ts=datetime.now(),
                    )
                    logger.info(f"单次监控完成，SQLite 已写入 {inserted} 行")
                    # 返回数据库路径，方便上层打印或后续使用
                    return str(self.sqlite_db_path)
                except Exception as e:
                    logger.error(f"单次监控写入SQLite失败: {e}")

        except Exception as e:
            logger.error(f"单次监控执行失败: {e}")
            import traceback
            logger.debug(f"单次监控执行失败详情: {traceback.format_exc()}")

        return None


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='realtime_monitor')
    parser.add_argument('--duration', type=int, default=120,
            help='监控时长（分钟），默认120分钟')
    parser.add_argument('--once', action='store_true',
                       help='只执行一次监控而不是持续监控')
    parser.add_argument('--stock-codes-file', type=str, default="/tmp/candidates/test.txt",
                       help='股票代码文件路径，每行一个股票代码')
    parser.add_argument('--data-mode', type=str, default='online',
                       choices=['file', 'online'],
                       help='数据加载模式：file(从文件加载) 或 online(在线获取)，默认file')

    args = parser.parse_args()

    # 创建监控器
    monitor = RealTimeStockMonitor(data_mode=args.data_mode)

    # 设置股票代码文件参数
    stock_codes_file = getattr(args, 'stock_codes_file', None)

    if args.once:
        # 执行单次监控（不检查交易时间）
        result = monitor.run_once(stock_codes_file, check_trading_time=False)
        if result:
            print(f"单次监控完成，数据保存至: {result}")
        else:
            print("单次监控失败")
    else:
        # 执行持续监控（检查交易时间，不保存CSV）
        monitor.run_monitoring(args.duration, stock_codes_file)


if __name__ == '__main__':
    main()
