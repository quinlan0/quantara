#!/usr/bin/env python3
"""
股票基本信息更新脚本

使用 StockBasicInfoManager 更新股票基本信息到缓存。
这是一个便捷的命令行工具。

使用方法:
    python scripts/update_stock_basic_info.py          # 更新股票基本信息
    python scripts/update_stock_basic_info.py --help   # 显示帮助信息
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="更新股票基本信息到缓存",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/update_stock_basic_info.py

更新完成后，您可以这样使用数据:
    from common.data_getter import DataGetter
    getter = DataGetter()
    stocks = getter.get_stock_basic_info(['000001', '600000'])
        """
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，不显示详细信息'
    )

    args = parser.parse_args()

    try:
        from common.stock_basic_info_manager import StockBasicInfoManager

        if not args.quiet:
            print("🔄 开始更新股票基本信息...")
            print("这可能需要几分钟时间，请耐心等待...")
            print()

        # 更新数据
        StockBasicInfoManager.update_stock_basic_info()

        if not args.quiet:
            print()
            print("✅ 股票基本信息更新完成！")
            print()
            print("现在您可以使用 DataGetter 获取股票信息：")
            print("  from common.data_getter import DataGetter")
            print("  getter = DataGetter()")
            print("  stocks = getter.get_stock_basic_info(['000001', '600000'])")

        return 0

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保在项目根目录下运行此脚本")
        return 1

    except KeyboardInterrupt:
        print("\n⚠️  操作被用户中断")
        return 130

    except Exception as e:
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())