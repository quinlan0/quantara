"""
测试utils模块的功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from common.utils import StockCodeUtils, DataProcessingUtils
    from common.utils import transform_code, transform_code_for_xtdata, normalize_stock_codes

    def test_stock_code_utils():
        """测试StockCodeUtils类"""
        print("=== 测试 StockCodeUtils ===")

        # 测试transform_code
        test_cases = [
            ('000001.SH', '000001'),
            ('SH000001', '000001'),
            ('000001sh', '000001'),
            ('sh000001', '000001'),
            ('000001', '000001'),
            ('600000.SH', '600000'),
            ('SZ000002', '000002'),
        ]

        print("测试 transform_code:")
        for input_code, expected in test_cases:
            result = StockCodeUtils.transform_code(input_code)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {input_code} -> {result} (期望: {expected})")

        # 测试transform_code_for_xtdata
        xtdata_cases = [
            ('000001', '000001.SZ'),
            ('600000', '600000.SH'),
            ('000001.SZ', '000001.SZ'),
            ('300001', '300001.SZ'),
            ('800001', '800001.BJ'),
        ]

        print("\n测试 transform_code_for_xtdata:")
        for input_code, expected in xtdata_cases:
            result = StockCodeUtils.transform_code_for_xtdata(input_code)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {input_code} -> {result} (期望: {expected})")

        # 测试extract_clean_code
        print("\n测试 extract_clean_code:")
        extract_cases = [
            ('000001.SH', '000001'),
            ('SH000001股票', '000001'),
            ('代码:600000', '600000'),
            ('000001', '000001'),
        ]

        for input_str, expected in extract_cases:
            result = StockCodeUtils.extract_clean_code(input_str)
            status = "✓" if result == expected else "✗"
            print(f"  {status} '{input_str}' -> '{result}' (期望: '{expected}')")

        # 测试批量处理
        print("\n测试批量处理:")
        codes = ['000001.SH', 'SH600000', '000002sz', '300001']
        clean_codes = StockCodeUtils.normalize_stock_codes(codes)
        xtdata_codes = StockCodeUtils.format_stock_codes_for_xtdata(clean_codes)

        print(f"  原始代码: {codes}")
        print(f"  清洁代码: {clean_codes}")
        print(f"  xtdata格式: {xtdata_codes}")

    def test_data_processing_utils():
        """测试DataProcessingUtils类"""
        print("\n=== 测试 DataProcessingUtils ===")

        # 测试safe_strip
        print("测试 safe_strip:")
        strip_cases = [
            (None, ''),
            ('  hello  ', 'hello'),
            (123, '123'),
            ('', ''),
        ]

        for input_val, expected in strip_cases:
            result = DataProcessingUtils.safe_strip(input_val)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {input_val!r} -> {result!r} (期望: {expected!r})")

        # 测试safe_int和safe_float
        print("\n测试 safe_int 和 safe_float:")
        num_cases = [
            ('123', 123, 123.0),
            ('123.45', 123, 123.45),
            ('invalid', 0, 0.0),
            (None, 0, 0.0),
        ]

        for input_val, expected_int, expected_float in num_cases:
            result_int = DataProcessingUtils.safe_int(input_val)
            result_float = DataProcessingUtils.safe_float(input_val)
            status_int = "✓" if result_int == expected_int else "✗"
            status_float = "✓" if result_float == expected_float else "✗"
            print(f"  {status_int} safe_int({input_val!r}) -> {result_int} (期望: {expected_int})")
            print(f"  {status_float} safe_float({input_val!r}) -> {result_float} (期望: {expected_float})")

        # 测试merge_dicts
        print("\n测试 merge_dicts:")
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'b': 20, 'c': 3}
        dict3 = {'c': 30, 'd': 4}

        result = DataProcessingUtils.merge_dicts(dict1, dict2, dict3)
        expected = {'a': 1, 'b': 20, 'c': 30, 'd': 4}

        status = "✓" if result == expected else "✗"
        print(f"  {status} 合并结果: {result}")
        print(f"      期望结果: {expected}")

    def test_backward_compatibility():
        """测试向后兼容函数"""
        print("\n=== 测试向后兼容函数 ===")

        # 测试模块级函数
        test_code = '000001.SH'
        result1 = transform_code(test_code)
        result2 = StockCodeUtils.transform_code(test_code)

        status = "✓" if result1 == result2 else "✗"
        print(f"  {status} transform_code('{test_code}') -> '{result1}'")
        print(f"      与 StockCodeUtils.transform_code 结果一致: {result1 == result2}")

        # 测试批量函数
        codes = ['000001.SH', '600000']
        result1 = normalize_stock_codes(codes)
        result2 = StockCodeUtils.normalize_stock_codes(codes)

        status = "✓" if result1 == result2 else "✗"
        print(f"  {status} normalize_stock_codes({codes}) -> {result1}")
        print(f"      与 StockCodeUtils.normalize_stock_codes 结果一致: {result1 == result2}")

    def main():
        """主测试函数"""
        print("开始测试 common/utils.py 模块")
        print("=" * 50)

        try:
            test_stock_code_utils()
            test_data_processing_utils()
            test_backward_compatibility()

            print("\n" + "=" * 50)
            print("✅ 所有测试完成！utils模块功能正常。")

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
    print("请确保common模块在Python路径中")
    sys.exit(1)