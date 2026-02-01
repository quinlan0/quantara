#!/usr/bin/env python3
"""
测试股票代码格式转换功能
"""

def test_code_format_conversion():
    """测试代码格式转换"""
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from data_getter import DataGetter

    getter = DataGetter()

    # 测试transform_code方法
    test_cases = [
        ('000001.SH', '000001'),
        ('SH000001', '000001'),
        ('000001sh', '000001'),
        ('sh000001', '000001'),
        ('000001', '000001'),
        ('600000.SH', '600000'),
        ('SZ000002', '000002'),
    ]

    print("测试 transform_code 方法:")
    for input_code, expected in test_cases:
        try:
            result = DataGetter.transform_code(input_code)
            if result == expected:
                print(f"✅ {input_code} -> {result}")
            else:
                print(f"❌ {input_code} -> {result} (期望: {expected})")
        except Exception as e:
            print(f"❌ {input_code} -> 错误: {e}")

    # 测试transform_code_for_xtdata方法
    xtdata_test_cases = [
        ('000001', '000001.SZ'),
        ('600000', '600000.SH'),
        ('000002', '000002.SZ'),
        ('300001', '300001.SZ'),
        ('000001.SH', '000001.SZ'),
        ('SH600000', '600000.SH'),
    ]

    print("\n测试 transform_code_for_xtdata 方法:")
    for input_code, expected in xtdata_test_cases:
        try:
            result = DataGetter.transform_code_for_xtdata(input_code)
            if result == expected:
                print(f"✅ {input_code} -> {result}")
            else:
                print(f"❌ {input_code} -> {result} (期望: {expected})")
        except Exception as e:
            print(f"❌ {input_code} -> 错误: {e}")

if __name__ == "__main__":
    test_code_format_conversion()