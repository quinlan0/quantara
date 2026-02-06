#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 StockDataProvider 模块
"""

import sys
import pandas as pd
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_stock_data_class():
    """测试 StockData 类"""
    from monitor.stock_data_provider import StockData

    # 测试基本属性
    stock = StockData(code="000001", name="平安银行", prev_close=10.5)
    assert stock.code == "000001"
    assert stock.get_name() == "平安银行"
    assert stock.get_prev_close() == 10.5
    assert not stock.has_history()

    # 测试默认值
    stock_empty = StockData(code="000002")
    assert stock_empty.get_name(default='') == ''
    assert stock_empty.get_prev_close(default=0.0) == 0.0

    # 测试带历史数据
    history_df = pd.DataFrame({
        'close': [10.0, 10.5, 11.0],
        'volume': [1000, 1100, 1200]
    })
    stock_with_history = StockData(code="000003", history_df=history_df)
    assert stock_with_history.has_history()
    # 没有 prev_close 时从 history_df 获取
    assert stock_with_history.get_prev_close() == 11.0

    print("✓ StockData 类测试通过")
    return True


def test_stock_data_provider_init():
    """测试 StockDataProvider 初始化"""
    from monitor.stock_data_provider import StockDataProvider

    # 测试文件模式初始化
    provider_file = StockDataProvider(
        mode=StockDataProvider.MODE_FILE,
        file_path="/tmp/nonexistent.pkl"
    )
    assert provider_file.mode == StockDataProvider.MODE_FILE
    assert provider_file.file_path == Path("/tmp/nonexistent.pkl")

    # 测试在线模式初始化
    provider_online = StockDataProvider(
        mode=StockDataProvider.MODE_ONLINE,
        data_getter=None,
        history_count=50
    )
    assert provider_online.mode == StockDataProvider.MODE_ONLINE
    assert provider_online.history_count == 50

    print("✓ StockDataProvider 初始化测试通过")
    return True


def test_stock_data_provider_cache():
    """测试 StockDataProvider 缓存功能"""
    from monitor.stock_data_provider import StockDataProvider, StockData

    provider = StockDataProvider(mode=StockDataProvider.MODE_FILE)

    # 手动添加数据到缓存
    provider._data_cache["000001"] = StockData(
        code="000001",
        name="测试股票",
        prev_close=10.0
    )
    provider._data_cache["000002"] = StockData(
        code="000002",
        name="测试股票2",
        prev_close=20.0
    )

    # 测试获取
    assert provider.has_data("000001")
    assert provider.has_data("000002")
    assert not provider.has_data("000003")

    stock = provider.get_stock_data("000001")
    assert stock is not None
    assert stock.code == "000001"
    assert stock.get_name() == "测试股票"

    # 测试获取所有代码
    codes = provider.get_all_codes()
    assert len(codes) == 2
    assert "000001" in codes
    assert "000002" in codes

    # 测试清除缓存
    provider.clear_cache()
    assert len(provider.get_all_codes()) == 0

    print("✓ StockDataProvider 缓存功能测试通过")
    return True


def test_real_time_monitor_with_provider():
    """测试 RealTimeStockMonitor 与 StockDataProvider 集成"""
    from monitor.real_time_monitor import RealTimeStockMonitor

    # 测试文件模式初始化
    monitor_file = RealTimeStockMonitor(data_mode='file')
    assert monitor_file.data_mode == RealTimeStockMonitor.DATA_MODE_FILE
    assert monitor_file.stock_data_provider is None  # 延迟初始化

    # 测试在线模式初始化
    monitor_online = RealTimeStockMonitor(data_mode='online')
    assert monitor_online.data_mode == RealTimeStockMonitor.DATA_MODE_ONLINE

    print("✓ RealTimeStockMonitor 与 StockDataProvider 集成测试通过")
    return True


def test_calculate_indicator_with_missing_data():
    """测试缺失历史数据时的指标计算（使用实时数据兜底）"""
    from monitor.real_time_monitor import RealTimeStockMonitor
    from monitor.stock_data_provider import StockDataProvider, StockData
    import pandas as pd

    monitor = RealTimeStockMonitor(data_mode='online')

    # 手动设置一个空的 provider
    monitor.stock_data_provider = StockDataProvider(mode=StockDataProvider.MODE_ONLINE)

    # 添加一个没有历史数据的股票
    monitor.stock_data_provider._data_cache["000001"] = StockData(
        code="000001",
        name=None,  # 没有名称
        prev_close=None,  # 没有前一日收盘价
        history_df=None  # 没有历史数据
    )

    # 模拟实时数据（包含 pre_close）- 假设数据有效，不需要做有效性检查
    real_time_tick = pd.DataFrame([{
        'close': 10.5,
        'open': 10.0,
        'high': 11.0,
        'low': 9.5,
        'volume': 1000000,
        'pre_close': 10.0
    }])

    # 计算指标（调用方确保 real_time_tick 有效）
    indicator = monitor._calculate_single_stock_indicator("000001", real_time_tick)

    assert indicator is not None
    assert indicator['股票代码'] == "000001"
    assert indicator['股票名称'] == ''  # 名称应为空字符串
    assert indicator['当前价格'] == 10.5
    assert indicator['当前涨跌幅'] == 5.0  # (10.5 - 10.0) / 10.0 * 100

    print("✓ 缺失历史数据时的指标计算测试通过")
    return True


def test_calculate_indicator_with_dict_data():
    """测试使用字典格式实时数据的指标计算"""
    from monitor.real_time_monitor import RealTimeStockMonitor
    from monitor.stock_data_provider import StockDataProvider, StockData

    monitor = RealTimeStockMonitor(data_mode='online')
    monitor.stock_data_provider = StockDataProvider(mode=StockDataProvider.MODE_ONLINE)

    monitor.stock_data_provider._data_cache["000002"] = StockData(
        code="000002",
        name="测试股票",
        prev_close=20.0,
        history_df=None
    )

    # 字典格式的实时数据
    real_time_tick = {
        'close': 21.0,
        'open': 20.5,
        'high': 21.5,
        'low': 20.0,
        'volume': 500000,
        'pre_close': 20.0
    }

    indicator = monitor._calculate_single_stock_indicator("000002", real_time_tick)

    assert indicator is not None
    assert indicator['股票代码'] == "000002"
    assert indicator['股票名称'] == "测试股票"
    assert indicator['当前价格'] == 21.0
    assert indicator['当前涨跌幅'] == 5.0  # (21.0 - 20.0) / 20.0 * 100

    print("✓ 字典格式实时数据的指标计算测试通过")
    return True


def main():
    """主测试函数"""
    print("开始测试 StockDataProvider 模块...")

    tests = [
        ("StockData 类测试", test_stock_data_class),
        ("StockDataProvider 初始化测试", test_stock_data_provider_init),
        ("StockDataProvider 缓存功能测试", test_stock_data_provider_cache),
        ("RealTimeStockMonitor 集成测试", test_real_time_monitor_with_provider),
        ("缺失历史数据时的指标计算测试", test_calculate_indicator_with_missing_data),
        ("字典格式实时数据的指标计算测试", test_calculate_indicator_with_dict_data),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n运行测试: {test_name}")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} 失败: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n测试结果: {passed}/{total} 通过")

    if passed == total:
        print("所有测试通过！")
        return True
    else:
        print("部分测试失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
