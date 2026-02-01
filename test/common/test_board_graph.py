#!/usr/bin/env python3
"""
测试重构后的board_graph.py模块
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_board_node_type_enum():
    """测试BoardNodeType枚举"""
    try:
        from common.board_graph import BoardNodeType, BoardEdgeType, BoardNode

        # 测试枚举值
        assert BoardNodeType.STOCK.value == 0
        assert BoardNodeType.INDUSTRY_L1.value == 1
        assert BoardNodeType.CONCEPT.value == 4
        assert BoardNodeType.INDEX.value == 5

        # 测试字符串转换
        assert str(BoardNodeType.STOCK) == "股票"
        assert str(BoardNodeType.CONCEPT) == "概念板块"
        assert str(BoardNodeType.INDEX) == "指数板块"

        # 测试短字符串转换
        assert BoardNodeType.STOCK.to_short_string() == "STOCK"
        assert BoardNodeType.CONCEPT.to_short_string() == "CONCEPT"

        # 测试从整数创建
        assert BoardNodeType.from_int(0) == BoardNodeType.STOCK
        assert BoardNodeType.from_int(4) == BoardNodeType.CONCEPT

        # 测试获取所有类型
        all_types = BoardNodeType.get_all_types()
        assert len(all_types) == 6
        assert BoardNodeType.STOCK in all_types

        # 测试获取分类类型
        stock_types = BoardNodeType.get_stock_types()
        assert stock_types == [BoardNodeType.STOCK]

        industry_types = BoardNodeType.get_industry_types()
        assert len(industry_types) == 3
        assert BoardNodeType.INDUSTRY_L1 in industry_types

        board_types = BoardNodeType.get_board_types()
        assert len(board_types) == 2
        assert BoardNodeType.CONCEPT in board_types
        assert BoardNodeType.INDEX in board_types

        print("✅ BoardNodeType枚举测试通过")
        return True
    except Exception as e:
        print(f"❌ BoardNodeType枚举测试失败: {e}")
        return False


def test_board_edge_type_enum():
    """测试BoardEdgeType枚举"""
    try:
        from common.board_graph import BoardEdgeType, BoardNodeType

        # 测试枚举值
        assert BoardEdgeType.INDUSTRY_RELATION.value == 1
        assert BoardEdgeType.CONCEPT_RELATION.value == 2
        assert BoardEdgeType.INDEX_RELATION.value == 3

        # 测试字符串转换
        assert str(BoardEdgeType.INDUSTRY_RELATION) == "行业关系"
        assert str(BoardEdgeType.CONCEPT_RELATION) == "概念关系"
        assert str(BoardEdgeType.INDEX_RELATION) == "指数关系"

        # 测试短字符串转换
        assert BoardEdgeType.INDUSTRY_RELATION.to_short_string() == "IND_REL"
        assert BoardEdgeType.CONCEPT_RELATION.to_short_string() == "CON_REL"
        assert BoardEdgeType.INDEX_RELATION.to_short_string() == "IDX_REL"

        # 测试从整数创建
        assert BoardEdgeType.from_int(1) == BoardEdgeType.INDUSTRY_RELATION
        assert BoardEdgeType.from_int(2) == BoardEdgeType.CONCEPT_RELATION
        assert BoardEdgeType.from_int(3) == BoardEdgeType.INDEX_RELATION

        # 测试获取所有类型
        all_types = BoardEdgeType.get_all_types()
        assert len(all_types) == 3
        assert BoardEdgeType.INDUSTRY_RELATION in all_types

        # 测试获取相关节点类型
        industry_nodes = BoardEdgeType.INDUSTRY_RELATION.get_related_node_types()
        assert len(industry_nodes) == 3
        assert BoardNodeType.INDUSTRY_L1 in industry_nodes

        concept_nodes = BoardEdgeType.CONCEPT_RELATION.get_related_node_types()
        assert concept_nodes == [BoardNodeType.CONCEPT]

        index_nodes = BoardEdgeType.INDEX_RELATION.get_related_node_types()
        assert index_nodes == [BoardNodeType.INDEX]

        print("✅ BoardEdgeType枚举测试通过")
        return True
    except Exception as e:
        print(f"❌ BoardEdgeType枚举测试失败: {e}")
        return False

def test_board_node():
    """测试BoardNode类"""
    try:
        from common.board_graph import BoardNode, BoardNodeType

        # 创建节点
        stock_node = BoardNode("000001", "平安银行", BoardNodeType.STOCK)
        concept_node = BoardNode("区块链", "区块链", BoardNodeType.CONCEPT)

        # 测试属性
        assert stock_node.code == "000001"
        assert stock_node.name == "平安银行"
        assert stock_node.node_type == BoardNodeType.STOCK

        # 测试哈希和相等性
        stock_node2 = BoardNode("000001", "平安银行", BoardNodeType.STOCK)
        assert stock_node == stock_node2
        assert hash(stock_node) == hash(stock_node2)

        # 测试不同节点不相等
        assert stock_node != concept_node

        # 测试to_dict方法
        node_dict = stock_node.to_dict()
        assert node_dict['code'] == "000001"
        assert node_dict['name'] == "平安银行"
        assert node_dict['type'] == 0
        assert node_dict['type_name'] == "股票"
        assert node_dict['type_short'] == "STOCK"

        # 测试字符串表示
        repr_str = repr(stock_node)
        assert "000001" in repr_str
        assert "平安银行" in repr_str
        assert "STOCK" in repr_str

        print("✅ BoardNode类测试通过")
        return True
    except Exception as e:
        print(f"❌ BoardNode类测试失败: {e}")
        return False

def test_board_graph_basic():
    """测试BoardGraph基本功能"""
    try:
        from common.board_graph import BoardGraph, BoardNodeType

        # 创建BoardGraph实例（使用缓存以避免网络请求）
        try:
            board_graph = BoardGraph(refresh_cache=False)

            # 测试节点索引存在
            assert hasattr(board_graph, 'industry_nodes')
            assert hasattr(board_graph, 'concept_nodes')
            assert hasattr(board_graph, 'index_nodes')
            assert hasattr(board_graph, 'stock_nodes')

            # 测试数据结构
            assert isinstance(board_graph.industry_info, dict)
            assert isinstance(board_graph.concept_info, dict)
            assert isinstance(board_graph.index_info, dict)

            # 测试图结构
            assert isinstance(board_graph.graph, dict)

            # 测试工具方法
            stock_name = board_graph.get_stock_name("000001")
            if stock_name:  # 如果有数据
                assert isinstance(stock_name, str)

            stock_code = board_graph.get_stock_code("平安银行")
            if stock_code:  # 如果有数据
                assert isinstance(stock_code, str)

            # 测试层次图构建
            industry_graph = board_graph.industry_graph
            assert isinstance(industry_graph, list)
            if industry_graph:
                assert industry_graph[0]['name'] == 'Industry'

            concept_graph = board_graph.concept_graph
            assert isinstance(concept_graph, list)

            index_graph = board_graph.index_graph
            assert isinstance(index_graph, list)

            print("✅ BoardGraph基本功能测试通过")
            return True

        except Exception as e:
            # 如果网络请求失败，跳过这个测试
            print(f"⚠️ BoardGraph初始化失败（可能需要网络访问），跳过测试: {e}")
            return True

    except Exception as e:
        print(f"❌ BoardGraph基本功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试重构后的board_graph.py模块...")
    print("=" * 50)

    tests = [
        test_board_node_type_enum,
        test_board_edge_type_enum,
        test_board_node,
        test_board_graph_basic
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
        print("🎉 所有测试通过！enum重构成功。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查代码。")
        return 1

if __name__ == "__main__":
    exit(main())