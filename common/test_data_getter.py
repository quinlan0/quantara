#!/usr/bin/env python3
"""
测试重构后的data_getter.py模块
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """测试导入"""
    try:
        from data_getter import DataGetter, DataFields
        print("✅ 模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_data_fields():
    """测试数据字段定义"""
    try:
        from data_getter import DataFields

        # 检查个股基本信息字段
        assert 'code' in DataFields.STOCK_BASIC_REQUIRED
        assert 'name' in DataFields.STOCK_BASIC_REQUIRED
        assert 'total_mv' in DataFields.STOCK_BASIC_OPTIONAL
        assert 'cir_mv' in DataFields.STOCK_BASIC_OPTIONAL
        assert 'pe' in DataFields.STOCK_BASIC_OPTIONAL
        assert 'pb' in DataFields.STOCK_BASIC_OPTIONAL
        assert 'total_shares' in DataFields.STOCK_BASIC_OPTIONAL
        assert 'cir_shares' in DataFields.STOCK_BASIC_OPTIONAL

        # 检查行情数据字段
        assert 'datetime' in DataFields.MARKET_DATA_REQUIRED
        assert 'open' in DataFields.MARKET_DATA_REQUIRED
        assert 'high' in DataFields.MARKET_DATA_REQUIRED
        assert 'low' in DataFields.MARKET_DATA_REQUIRED
        assert 'close' in DataFields.MARKET_DATA_REQUIRED
        assert 'volume' in DataFields.MARKET_DATA_REQUIRED
        assert 'amount' in DataFields.MARKET_DATA_REQUIRED
        assert 'pre_close' in DataFields.MARKET_DATA_REQUIRED

        print("✅ 数据字段定义正确")
        return True
    except Exception as e:
        print(f"❌ 数据字段定义测试失败: {e}")
        return False

def test_code_transform():
    """测试股票代码转换"""
    try:
        from data_getter import DataGetter

        # 测试transform_code方法（转换为6位数字格式）
        assert DataGetter.transform_code('000001.SH') == '000001'
        assert DataGetter.transform_code('SH000001') == '000001'
        assert DataGetter.transform_code('000001sh') == '000001'
        assert DataGetter.transform_code('sh000001') == '000001'
        assert DataGetter.transform_code('000001') == '000001'

        # 测试transform_code_for_xtdata方法（转换为xtdata格式）
        assert DataGetter.transform_code_for_xtdata('000001') == '000001.SZ'
        assert DataGetter.transform_code_for_xtdata('600000') == '600000.SH'
        assert DataGetter.transform_code_for_xtdata('000001.SZ') == '000001.SZ'

        print("✅ 股票代码转换功能正常")
        return True
    except Exception as e:
        print(f"❌ 股票代码转换测试失败: {e}")
        return False

def test_cache_path():
    """测试缓存路径生成"""
    try:
        from data_getter import DataGetter
        from pathlib import Path

        getter = DataGetter()

        # 测试缓存文件路径生成
        cache_file = getter._get_cache_file_path('stock_basic', 'all_stocks')
        expected_path = Path("/tmp/cache_output/quantara/data_getter/stock_basic_all_stocks.pkl")
        assert str(cache_file) == str(expected_path)

        # 测试带日期的缓存路径
        cache_file_with_date = getter._get_cache_file_path('market_data', '000001_1d_100', '20241231')
        expected_path_with_date = Path("/tmp/cache_output/quantara/data_getter/20241231/market_data_000001_1d_100.pkl")
        assert str(cache_file_with_date) == str(expected_path_with_date)

        print("✅ 缓存路径生成正常")
        return True
    except Exception as e:
        print(f"❌ 缓存路径测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试重构后的data_getter.py模块...")
    print("=" * 50)

    tests = [
        test_import,
        test_data_fields,
        test_code_transform,
        test_cache_path
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！重构成功。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查代码。")
        return 1

if __name__ == "__main__":
    exit(main())