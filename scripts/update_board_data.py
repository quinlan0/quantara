#!/usr/bin/env python3
"""
板块数据更新脚本

使用 BoardDataManager 更新板块数据到缓存。
这是一个便捷的命令行工具。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    try:
        from common.board_data_manager import BoardDataManager

        print("🔄 开始更新板块数据...")
        print("这可能需要几分钟时间，请耐心等待...")
        print()

        # 更新数据
        BoardDataManager.update_board_data()

        print()
        print("✅ 板块数据更新完成！")
        print()
        print("现在您可以使用 BoardGraph 加载数据：")
        print("  from common.board_graph import BoardGraph")
        print("  board_graph = BoardGraph()")

        return 0

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保在项目根目录下运行此脚本")
        return 1

    except Exception as e:
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())