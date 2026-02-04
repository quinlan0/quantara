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

    def __init__(self):
        self.cache_dir = Path("/tmp/cache_output/quantara/monitor/real_time_monitor")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储
        self.all_data = {}
        self.data_getter = DataGetter()

        # SQLite 存储（数据库文件与pkl在同一目录）
        self.sqlite_db_path = self.cache_dir / "real_time_monitor.db"
        self.sqlite_storage = RealTimeMonitorSQLite(self.sqlite_db_path)

        # 监控配置
        self.monitor_interval = 10  # 监控间隔（秒）
        self.max_retries = 3  # 最大重试次数

    def load_offline_data(self):
        """加载离线数据"""
        try:
            logger.info("开始加载离线数据...")

            # 确定数据目录
            data_dir = Path("/tmp") / "cache_output"
            if not data_dir.exists():
                logger.error(f"数据目录不存在: {data_dir}")
                return False
            stock_data_dict_dp = data_dir / "stock" / "update_stock_advanced_features.pkl"
            self.all_data['stock_data_dict'] = load_data(stock_data_dict_dp)
            '''
            stock_sectional_data_dp = data_dir / "stock" / "update_stock_sectional_data.pkl"
            self.all_data['stock_sectional_data'] = load_data(stock_sectional_data_dp)
            industry_bi_dp = data_dir / "board_infos" / "industry_board_infos.pkl"
            self.all_data['industry_board_infos'] = load_data(industry_bi_dp)
            concept_bi_dp = data_dir / "board_infos" / "concept_board_infos.pkl"
            self.all_data['concept_board_infos'] = load_data(concept_bi_dp)
            index_bi_dp = data_dir / "board_infos" / "index_board_infos.pkl"
            self.all_data['index_board_infos'] = load_data(index_bi_dp)
            all_boards_sectional_infos_dp = data_dir / "board_infos" / "board_sectional_infos.pkl"
            self.all_data['board_sectional_infos'] = load_data(all_boards_sectional_infos_dp)
            self.all_data['all_board_infos'], self.all_data['refined_infos_dict'] = load_data(data_dir / "board_infos" / "analysis_all_board_infos_day.pkl")
            '''
            logger.info("成功加载离线数据")
            return True

        except Exception as e:
            logger.error(f"加载离线数据失败: {e}")
            import traceback
            logger.debug(f"加载离线数据失败详情: {traceback.format_exc()}")
            return False

    def get_stock_list(self, stock_codes_file=None):
        """获取需要监控的股票列表

        Args:
            stock_codes_file: 股票代码文件路径，如果提供则优先从文件读取

        Returns:
            需要监控的股票代码列表
        """
        try:
            # 优先从文件读取股票代码
            file_stock_codes = []
            if stock_codes_file:
                if not os.path.exists(stock_codes_file):
                    logger.error(f"股票代码文件不存在: {stock_codes_file}")
                    sys.exit(1)

                try:
                    with open(stock_codes_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            code = line.strip()
                            if code:  # 跳过空行
                                file_stock_codes.append(code)
                    logger.info(f"从文件 {stock_codes_file} 读取到 {len(file_stock_codes)} 个股票代码")
                except Exception as e:
                    logger.error(f"读取股票代码文件失败 {stock_codes_file}: {e}")
                    sys.exit(1)
            file_stock_codes = list(set(file_stock_codes))

            # 从离线数据中提取所有可用的股票代码
            available_stock_codes = set()
            if 'stock_data_dict' in self.all_data:
                available_stock_codes = set(self.all_data['stock_data_dict'].keys())

            # 确定最终的股票代码列表
            if file_stock_codes:
                # 如果有文件指定的代码，取文件代码和可用代码的交集
                final_stock_codes = [code for code in file_stock_codes if code in available_stock_codes]

                logger.info(f"文件指定 {len(file_stock_codes)} 个代码，离线数据有 {len(available_stock_codes)} 个代码")
                logger.info(f"交集得到 {len(final_stock_codes)} 个有效股票代码")

                if len(final_stock_codes) == 0:
                    logger.warning("文件指定的股票代码与离线数据完全没有交集")
            else:
                # 如果没有文件指定，使用所有可用的股票代码
                final_stock_codes = list(available_stock_codes)
                logger.info(f"使用所有离线数据中的 {len(final_stock_codes)} 个股票代码")

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
        """计算单个股票的关键指标"""
        try:
            # 获取历史数据
            one_stock_data = self.all_data.get('stock_data_dict', {}).get(stock_code, None)
            if one_stock_data is None:
                logger.warning(f"股票 {stock_code} 没有历史数据")
                return None
            stock_data = one_stock_data['feat']
            stock_base_info = one_stock_data['base_info']

            # pandas DataFrame格式 - 每一行是每日的行情数据，最后一行是最新一天的数据
            if stock_data.empty:
                logger.warning(f"股票 {stock_code} 历史数据为空")
                return None

            # 获取最新历史数据（用于计算基准）
            latest_data = stock_data.iloc[-1] if len(stock_data) > 0 else None
            if latest_data is None:
                return None

            prev_close = latest_data['close']  # 上一日收盘价

            # 计算前五日涨跌幅
            if len(stock_data) >= 6:
                prev_5_close = stock_data.iloc[-6]['close']
                prev_5_change = (prev_close - prev_5_close) / prev_5_close * 100
            else:
                prev_5_change = 0.0

            # 计算前五日平均成交量
            if len(stock_data) >= 5:
                prev_5_volumes = stock_data.iloc[-5:]['volume'].mean()
            else:
                prev_5_volumes = 0.0

            # 处理实时数据
            current_price = prev_close  # 默认使用上一日收盘价
            open_price = prev_close     # 默认开盘价
            high_price = prev_close     # 默认最高价
            low_price = prev_close      # 默认最低价
            current_volume = 0.0        # 当日成交量

            # 检查是否有有效的实时数据
            has_valid_real_time_data = False

            if real_time_tick is not None:
                # 检查是否是有效的DataFrame
                if isinstance(real_time_tick, pd.DataFrame) and not real_time_tick.empty:
                    has_valid_real_time_data = True
                # 检查是否是有效的字典
                elif isinstance(real_time_tick, dict) and real_time_tick != -1:
                    has_valid_real_time_data = True

            if has_valid_real_time_data:
                try:
                    if isinstance(real_time_tick, pd.DataFrame):
                        # 处理DataFrame格式的实时数据
                        if not real_time_tick.empty:
                            latest_data = real_time_tick.iloc[-1]  # 获取最新一行数据
                            current_price = latest_data.get('close', prev_close)
                            open_price = latest_data.get('open', current_price)
                            high_price = latest_data.get('high', current_price)
                            low_price = latest_data.get('low', current_price)
                            current_volume = latest_data.get('volume', 0.0)
                    elif isinstance(real_time_tick, dict):
                        # 处理字典格式的实时数据
                        current_price = real_time_tick.get('close', prev_close)
                        open_price = real_time_tick.get('open', current_price)
                        high_price = real_time_tick.get('high', current_price)
                        low_price = real_time_tick.get('low', current_price)
                        current_volume = real_time_tick.get('volume', 0.0)

                    # 确保价格不为0或负数
                    if current_price <= 0:
                        current_price = prev_close
                    if open_price <= 0:
                        open_price = current_price
                    if high_price <= 0:
                        high_price = current_price
                    if low_price <= 0:
                        low_price = current_price

                except Exception as e:
                    logger.warning(f"处理股票 {stock_code} 实时数据失败: {e}，使用默认值")
                    logger.debug(f"股票 {stock_code} 实时数据详情: 类型={type(real_time_tick)}，内容={str(real_time_tick)[:200]}...")
                    # 保持默认值不变

            # 计算各项指标
            if len(stock_data) >= 2:
                prev_day_close = stock_data.iloc[-2]['close']
                prev_day_change = (prev_close - prev_day_close) / prev_day_close * 100 if prev_day_close != 0 else 0.0
            else:
                prev_day_change = 0.0  # 没有足够的历史数据，设为0

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
                '股票名称': stock_base_info['name'],
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
            logger.debug(f"股票 {stock_code} 指标计算失败详情: 历史数据={type(self.all_data.get('stock_data_dict', {}).get(stock_code))}，实时数据={type(real_time_tick)}，错误类型={type(e).__name__}")
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

            # 加载离线数据
            if not self.load_offline_data():
                logger.error("加载离线数据失败，退出监控")
                logger.debug("离线数据加载失败，检查数据目录和文件是否存在")
                return

            # 获取股票列表
            stock_codes = self.get_stock_list(stock_codes_file)
            if not stock_codes:
                logger.error("获取股票列表失败，退出监控")
                logger.debug("股票列表为空，检查离线数据是否正确加载")
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

            # 检查是否为交易时间（可选择性检查）
            if check_trading_time and not self.is_trading_time():
                current_time = datetime.now().strftime("%H:%M:%S")
                logger.warning(f"当前时间 {current_time} 不在A股交易时间内，无法执行监控")
                print(f"⏰ 当前时间 {current_time} 不在A股交易时间内，无法执行监控")
                return None

            # 加载离线数据
            if not self.load_offline_data():
                logger.error("加载离线数据失败")
                return

            # 获取股票列表
            stock_codes = self.get_stock_list(stock_codes_file)
            if not stock_codes:
                logger.error("获取股票列表失败")
                return

            # 获取实时数据
            real_time_data = self.data_getter.get_real_time_data(stock_codes)

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

    args = parser.parse_args()

    # 创建监控器
    monitor = RealTimeStockMonitor()

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
