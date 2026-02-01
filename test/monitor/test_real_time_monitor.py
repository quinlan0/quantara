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

def main():
    """主测试函数"""
    print("开始测试实时监控模块...")

    tests = [
        ("导入测试", test_imports),
        ("load_data函数测试", test_load_data),
        ("RealTimeStockMonitor类测试", test_monitor_class),
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