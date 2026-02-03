#!/usr/bin/env python3
"""
测试重构后的data_getter.py模块
"""

import sys
from pathlib import Path
# 添加项目根目录到Python路径，以便导入common模块
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.data_getter import DataGetter

getter = DataGetter()
codes = ['000001', '600000']

print("Data source:", getter.data_source)
res = getter.get_stock_basic_info(codes)
print('Stock basic info: ')
print(res)

res = getter.get_market_data(codes, period='1m', count=300)
print('Market data: ')
print(res)

res = getter.get_market_data(codes, period='1d', count=300)
print('Market data: ')
print(res)

res = getter.get_real_time_data(codes)
print('Real time data: ')
print(res)