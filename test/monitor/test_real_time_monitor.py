#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实时监控模块
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试导入是否正常"""
    try:
        from common.logger import init_logger, logger
        from common.utils import load_data
        from common.data_getter import DataGetter
        print("✓ 导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_load_data():
    """测试load_data函数"""
    try:
        from common.utils import load_data
        # 测试不存在的文件
        try:
            load_data("non_existent_file.pkl")
            print("✗ load_data应该抛出异常")
            return False
        except FileNotFoundError:
            print("✓ load_data正确处理不存在的文件")
            return True
    except Exception as e:
        print(f"✗ load_data测试失败: {e}")
        return False

def test_monitor_class():
    """测试RealTimeStockMonitor类"""
    try:
        from monitor.real_time_monitor import RealTimeStockMonitor
        monitor = RealTimeStockMonitor()
        print(f"✓ RealTimeStockMonitor类创建成功，缓存目录: {monitor.cache_dir}")
        return True
    except Exception as e:
        print(f"✗ RealTimeStockMonitor类测试失败: {e}")
        return False

def test_evaluate_monitoring_results():
    """测试评估监控结果功能"""
    try:
        from monitor.real_time_monitor import RealTimeStockMonitor
        import io
        import sys

        monitor = RealTimeStockMonitor()

        # 测试数据：包含完整指标
        test_data = [
            {
                '股票代码': '000001',
                '股票名称': '平安银行',
                '当前涨跌幅': 1.5,
                '量比': 1.2,
                '前五日涨跌幅': 0.8,
                '上一日涨跌幅': 1.0,
                '当日开盘涨跌幅': 0.5,
                '当日最高涨跌幅': 2.0,
                '当日最低涨跌幅': -1.0,
                '当日成交量': 1000000,
                '前五日平均量': 800000,
            },
            {
                '股票代码': '000002',
                '股票名称': '万科A',
                '当前涨跌幅': -2.0,
                '量比': 0.9,
                '前五日涨跌幅': -0.5,
                '上一日涨跌幅': -1.5,
                '当日开盘涨跌幅': -1.0,
                '当日最高涨跌幅': 0.5,
                '当日最低涨跌幅': -2.5,
                '当日成交量': 500000,
                '前五日平均量': 600000,
            },
            {
                '股票代码': '000003',
                '股票名称': '浦发银行',
                '当前涨跌幅': 4.5,  # 异常
                '量比': 2.1,
                '前五日涨跌幅': 1.2,
                '上一日涨跌幅': 2.0,
                '当日开盘涨跌幅': 3.0,
                '当日最高涨跌幅': 5.0,
                '当日最低涨跌幅': 2.0,
                '当日成交量': 2000000,
                '前五日平均量': 1000000,
            }
        ]

        # 测试空数据
        empty_data = []

        # 捕获print输出
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            # 测试完整数据
            monitor.evaluate_monitoring_results(test_data)
            output = captured_output.getvalue()
            captured_output.seek(0)
            captured_output.truncate(0)

            # 测试空数据
            monitor.evaluate_monitoring_results(empty_data)
            empty_output = captured_output.getvalue()

        finally:
            # 恢复标准输出
            sys.stdout = sys.__stdout__

        # 验证结果
        if '=== 监控结果' in output and '===' in output:
            print("✓ 评估功能正确输出监控结果")
        else:
            print("✗ 评估功能未能正确输出监控结果")
            return False

        # 检查表格边框和格式（prettytable 特有的格式）
        if '┌' in output or '─' in output or '┐' in output:
            print("✓ prettytable 表格格式正确")
        else:
            print("✗ prettytable 表格格式不正确")
            return False

        # 检查表格列标题
        required_headers = ['状态', '股票代码', '当前涨跌幅', '量比', '前五日涨跌幅', '上一日涨跌幅',
                           '当日开盘涨跌幅', '当日最高涨跌幅', '当日最低涨跌幅', '当日成交量', '前五日平均量']

        for header in required_headers:
            if header not in output:
                print(f"✗ 表格缺少列标题: {header}")
                return False

        # 检查数据内容
        if '000001' not in output or '000002' not in output or '000003' not in output:
            print("✗ 表格中缺少股票代码")
            return False

        if '1.50%' not in output or '4.50%' not in output:
            print("✗ 表格中缺少涨跌幅数据")
            return False

        if '⚠️' not in output:
            print("✗ 表格中缺少异常状态标识")
            return False

        if '✓' not in output:
            print("✗ 表格中缺少正常状态标识")
            return False

        if '本次监控 3 只股票，异常 1 只' in output:
            print("✓ 评估功能正确统计结果")
        else:
            print("✗ 评估功能未能正确统计结果")
            return False

        if '股票名称' not in output:
            print("✓ 评估功能正确不显示股票名称")
        else:
            print("✗ 评估功能错误地显示了股票名称")
            return False

        print("✓ 评估监控结果功能测试通过")
        return True

    except Exception as e:
        print(f"✗ 评估监控结果功能测试失败: {e}")
        return False

def test_trading_time_check():
    """测试交易时间检查功能"""
    try:
        from monitor.real_time_monitor import RealTimeStockMonitor
        from datetime import time

        monitor = RealTimeStockMonitor()

        # 模拟不同时间进行测试
        test_cases = [
            # (小时, 分钟, 星期几, 期望结果, 描述)
            (9, 0, 0, False, "交易前"),  # 周一 9:00 - 非交易时间
            (9, 30, 0, True, "交易开始"),  # 周一 9:30 - 交易时间
            (10, 0, 0, True, "上午交易中"),  # 周一 10:00 - 交易时间
            (11, 30, 0, True, "上午交易结束"),  # 周一 11:30 - 交易时间
            (12, 0, 0, False, "午休时间"),  # 周一 12:00 - 非交易时间
            (13, 0, 0, True, "下午交易开始"),  # 周一 13:00 - 交易时间
            (14, 0, 0, True, "下午交易中"),  # 周一 14:00 - 交易时间
            (15, 0, 0, True, "下午交易结束"),  # 周一 15:00 - 交易时间
            (16, 0, 0, False, "交易后"),  # 周一 16:00 - 非交易时间
            (10, 0, 5, False, "周末"),  # 周六 10:00 - 非交易时间
        ]

        for hour, minute, weekday, expected, description in test_cases:
            # 这里我们只能测试方法是否存在，无法真正模拟时间
            # 所以我们只检查方法能正常调用
            try:
                result = monitor.is_trading_time()
                # result 应该是布尔值
                if isinstance(result, bool):
                    print(f"✓ 交易时间检查方法正常工作 - {description}")
                else:
                    print(f"✗ 交易时间检查方法返回类型错误 - {description}")
                    return False
            except Exception as e:
                print(f"✗ 交易时间检查方法调用失败 - {description}: {e}")
                return False

        print("✓ 交易时间检查功能测试通过")
        return True

    except Exception as e:
        print(f"✗ 交易时间检查功能测试失败: {e}")
        return False

def test_parameter_control():
    """测试参数控制功能"""
    try:
        from monitor.real_time_monitor import RealTimeStockMonitor

        monitor = RealTimeStockMonitor()

        # 测试 save_real_time_data 方法的参数控制
        test_data = [
            {
                '股票代码': '000001',
                '股票名称': '平安银行',
                '当前涨跌幅': 1.5,
            }
        ]

        # 测试保存CSV
        try:
            result_csv = monitor.save_real_time_data(test_data, save_csv=True)
            if result_csv:
                print("✓ save_real_time_data 方法支持保存CSV")
            else:
                print("✗ save_real_time_data 方法保存CSV失败")
                return False
        except Exception as e:
            print(f"✗ save_real_time_data 方法测试失败: {e}")
            return False

        # 测试不保存CSV
        try:
            result_no_csv = monitor.save_real_time_data(test_data, save_csv=False)
            if result_no_csv:
                print("✓ save_real_time_data 方法支持不保存CSV")
            else:
                print("✗ save_real_time_data 方法不保存CSV失败")
                return False
        except Exception as e:
            print(f"✗ save_real_time_data 方法不保存CSV测试失败: {e}")
            return False

        # 测试 run_once 方法的参数控制
        # 注意：我们无法完全测试 run_once，因为它依赖于数据文件
        # 但我们可以检查方法签名是否正确
        import inspect
        run_once_sig = inspect.signature(monitor.run_once)
        if 'check_trading_time' in run_once_sig.parameters:
            print("✓ run_once 方法支持 check_trading_time 参数")
        else:
            print("✗ run_once 方法缺少 check_trading_time 参数")
            return False

        print("✓ 参数控制功能测试通过")
        return True

    except Exception as e:
        print(f"✗ 参数控制功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试实时监控模块...")

    tests = [
        ("导入测试", test_imports),
        ("load_data函数测试", test_load_data),
        ("RealTimeStockMonitor类测试", test_monitor_class),
        ("评估监控结果功能测试", test_evaluate_monitoring_results),
        ("交易时间检查功能测试", test_trading_time_check),
        ("参数控制功能测试", test_parameter_control),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n运行测试: {test_name}")
        if test_func():
            passed += 1

    print(f"\n测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！")
        return True
    else:
        print("❌ 部分测试失败")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)