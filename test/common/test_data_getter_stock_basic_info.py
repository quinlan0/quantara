"""
测试 DataGetter.get_stock_basic_info 接口的功能
"""

import sys
import os
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from common.data_getter import DataGetter
    from common.utils import StockCodeUtils


    def test_get_specific_stocks():
        """测试获取指定股票信息"""
        print("\n=== 测试获取指定股票信息 ===")

        getter = DataGetter()

        # 测试获取单只股票
        df_single = getter.get_stock_basic_info('000001')
        assert len(df_single) == 1, "应该返回1只股票"
        assert df_single.iloc[0]['code'] == '000001', "股票代码应该正确"

        # 测试获取多只股票
        df_multi = getter.get_stock_basic_info(['000001', '600000'])
        assert len(df_multi) == 2, "应该返回2只股票"
        assert set(df_multi['code'].tolist()) == {'000001', '600000'}, "股票代码应该正确"

        # 测试股票代码格式转换
        df_converted = getter.get_stock_basic_info(['000001.SH', 'SZ000002'])
        assert len(df_converted) == 2, "应该返回2只股票"
        assert set(df_converted['code'].tolist()) == {'000001', '000002'}, "代码格式转换应该正确"

        print("✅ 指定股票信息获取测试通过")


    def test_stock_code_normalization():
        """测试股票代码标准化功能"""
        print("\n=== 测试股票代码标准化 ===")

        getter = DataGetter()

        # 测试各种代码格式
        test_cases = [
            ('000001', ['000001']),
            (['000001'], ['000001']),
            (['000001.SH', 'SZ600000'], ['000001', '600000']),
            (['sh000001', '600000sz'], ['000001', '600000']),
        ]

        for input_codes, expected_codes in test_cases:
            df = getter.get_stock_basic_info(input_codes)
            actual_codes = sorted(df['code'].tolist())
            expected_codes = sorted(expected_codes)
            assert actual_codes == expected_codes, f"代码转换失败: {input_codes} -> {actual_codes}, 期望: {expected_codes}"

        print("✅ 股票代码标准化测试通过")

    def test_error_handling():
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")
        getter = DataGetter()

        try:
            getter.get_stock_basic_info()
        except Exception as e:
            assert "加载股票基本信息缓存失败" in str(e)
            print("✅ 正确处理缓存文件损坏的情况")

    def main():
        """主测试函数"""
        print("开始测试 DataGetter.get_stock_basic_info 接口")
        print("=" * 60)

        try:
            test_get_specific_stocks()
            test_stock_code_normalization()
            test_error_handling()

            print("\n" + "=" * 60)
            print("✅ 所有测试完成！DataGetter.get_stock_basic_info 接口测试通过。")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

            return False

        return True

    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保 common 模块在 Python 路径中")
    sys.exit(1)