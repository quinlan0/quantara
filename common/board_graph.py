"""
板块图管理模块
构建和管理股票与板块（行业、概念、指数）之间的关系图
"""

import os
import pickle
import json
import datetime
import time
import akshare as ak
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

from tqdm import tqdm

# 导入自定义模块
from .utils import StockCodeUtils, DataProcessingUtils

class BoardNodeType(Enum):
    """板块节点类型枚举"""
    STOCK = 0          # 股票
    INDUSTRY_L1 = 1    # 一级行业
    INDUSTRY_L2 = 2    # 二级行业
    INDUSTRY_L3 = 3    # 三级行业
    CONCEPT = 4        # 概念板块
    INDEX = 5          # 指数板块

    def __str__(self) -> str:
        """转换为可读的字符串"""
        descriptions = {
            BoardNodeType.STOCK: "股票",
            BoardNodeType.INDUSTRY_L1: "一级行业",
            BoardNodeType.INDUSTRY_L2: "二级行业",
            BoardNodeType.INDUSTRY_L3: "三级行业",
            BoardNodeType.CONCEPT: "概念板块",
            BoardNodeType.INDEX: "指数板块"
        }
        return descriptions.get(self, f"未知类型({self.value})")

    def to_short_string(self) -> str:
        """转换为简短字符串"""
        short_names = {
            BoardNodeType.STOCK: "STOCK",
            BoardNodeType.INDUSTRY_L1: "IND_L1",
            BoardNodeType.INDUSTRY_L2: "IND_L2",
            BoardNodeType.INDUSTRY_L3: "IND_L3",
            BoardNodeType.CONCEPT: "CONCEPT",
            BoardNodeType.INDEX: "INDEX"
        }
        return short_names.get(self, f"UNK_{self.value}")

    @classmethod
    def from_int(cls, value: int) -> 'BoardNodeType':
        """从整数创建枚举值"""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"无效的节点类型值: {value}")

    @classmethod
    def get_all_types(cls) -> List['BoardNodeType']:
        """获取所有节点类型"""
        return list(cls)

    @classmethod
    def get_stock_types(cls) -> List['BoardNodeType']:
        """获取股票相关类型"""
        return [cls.STOCK]

    @classmethod
    def get_industry_types(cls) -> List['BoardNodeType']:
        """获取行业相关类型"""
        return [cls.INDUSTRY_L1, cls.INDUSTRY_L2, cls.INDUSTRY_L3]

    @classmethod
    def get_board_types(cls) -> List['BoardNodeType']:
        """获取板块相关类型（概念和指数）"""
        return [cls.CONCEPT, cls.INDEX]


class BoardEdgeType(Enum):
    """板块边关系类型枚举"""
    INDUSTRY_RELATION = 1   # 行业板块与股票的关系
    CONCEPT_RELATION = 2    # 概念板块与股票的关系
    INDEX_RELATION = 3      # 指数板块与股票的关系

    def __str__(self) -> str:
        """转换为可读的字符串"""
        descriptions = {
            BoardEdgeType.INDUSTRY_RELATION: "行业关系",
            BoardEdgeType.CONCEPT_RELATION: "概念关系",
            BoardEdgeType.INDEX_RELATION: "指数关系"
        }
        return descriptions.get(self, f"未知关系({self.value})")

    def to_short_string(self) -> str:
        """转换为简短字符串"""
        short_names = {
            BoardEdgeType.INDUSTRY_RELATION: "IND_REL",
            BoardEdgeType.CONCEPT_RELATION: "CON_REL",
            BoardEdgeType.INDEX_RELATION: "IDX_REL"
        }
        return short_names.get(self, f"UNK_REL_{self.value}")

    @classmethod
    def from_int(cls, value: int) -> 'BoardEdgeType':
        """从整数创建枚举值"""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"无效的边关系类型值: {value}")

    @classmethod
    def get_all_types(cls) -> List['BoardEdgeType']:
        """获取所有边关系类型"""
        return list(cls)

    def get_related_node_types(self) -> List[BoardNodeType]:
        """获取与此边关系相关的节点类型"""
        relations = {
            BoardEdgeType.INDUSTRY_RELATION: BoardNodeType.get_industry_types(),
            BoardEdgeType.CONCEPT_RELATION: [BoardNodeType.CONCEPT],
            BoardEdgeType.INDEX_RELATION: [BoardNodeType.INDEX]
        }
        return relations.get(self, [])


@dataclass
class BoardNode:
    """板块节点"""
    code: str
    name: str
    node_type: BoardNodeType

    def __hash__(self):
        return hash((self.code, self.node_type))

    def __eq__(self, other):
        if not isinstance(other, BoardNode):
            return False
        return self.code == other.code and self.node_type == other.node_type

    def __repr__(self):
        return f"BoardNode(code='{self.code}', name='{self.name}', type={self.node_type.name})"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'code': self.code,
            'name': self.name,
            'type': self.node_type.value,
            'type_name': str(self.node_type),
            'type_short': self.node_type.to_short_string()
        }


class BoardGraph:
    """
    板块图管理类

    构建和管理股票与板块之间的关系网络：
    - 节点类型: STOCK=股票, INDUSTRY_L1=一级行业, INDUSTRY_L2=二级行业,
              INDUSTRY_L3=三级行业, CONCEPT=概念板块, INDEX=指数板块
    - 边关系: INDUSTRY_RELATION=行业关系, CONCEPT_RELATION=概念关系, INDEX_RELATION=指数关系
    """

    # 缓存目录 - 与 date_info 目录保持一致
    CACHE_DIR = Path("/tmp/cache_output/quantara/date_info")
    BOARD_INFO_CACHE = CACHE_DIR / "board_info.pkl"

    def __init__(self, cache_dir: Optional[str] = None, refresh_cache: bool = False):
        """
        初始化板块图

        Args:
            cache_dir: 缓存目录路径
            refresh_cache: 是否强制刷新缓存
        """
        if cache_dir:
            self.CACHE_DIR = Path(cache_dir)
            self.BOARD_INFO_CACHE = self.CACHE_DIR / "board_info.pkl"

        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # 数据存储
        self.industry_info: Dict[str, Dict] = {}
        self.concept_info: Dict[str, Dict] = {}
        self.index_info: Dict[str, Dict] = {}

        # 节点索引
        self.industry_nodes: Dict[str, BoardNode] = {}
        self.concept_nodes: Dict[str, BoardNode] = {}
        self.index_nodes: Dict[str, BoardNode] = {}
        self.stock_nodes: Dict[str, BoardNode] = {}

        # 股票代码名称映射
        self.stock_code_name_dict: Dict[str, str] = {}
        self.stock_name_code_dict: Dict[str, str] = {}

        # 关系图: key为源节点，value为{目标节点: 权重}的字典
        self.graph: Dict[BoardNode, Dict[BoardNode, int]] = {}

        # 分层图结构
        self.industry_graph: List[Dict] = []
        self.concept_graph: List[Dict] = []
        self.index_graph: List[Dict] = []

        # 加载数据
        self._load_board_data(refresh_cache)

        # 构建图结构
        self.construct_graph()
        self.industry_graph = self.construct_industry_graph(self.industry_info)
        self.concept_graph = self.construct_concept_graph(self.concept_info)
        self.index_graph = self.construct_index_graph(self.index_info)

    def _load_board_data(self, refresh: bool = False) -> None:
        """
        加载板块数据

        只负责读取离线缓存文件，如果缓存文件不存在则报错。
        数据获取和保存请使用 BoardDataManager。

        Args:
            refresh: 不再使用此参数，仅为了向后兼容

        Raises:
            FileNotFoundError: 当缓存文件不存在时
            Exception: 当缓存文件读取失败时
        """
        if not self.BOARD_INFO_CACHE.exists():
            error_msg = f"板块数据缓存文件不存在: {self.BOARD_INFO_CACHE}\n" \
                       f"请先使用 BoardDataManager 更新数据:\n" \
                       f"  python -m common.board_data_manager update"
            raise FileNotFoundError(error_msg)

        try:
            with open(self.BOARD_INFO_CACHE, 'rb') as f:
                board_info = pickle.load(f)

                # 加载基本数据
                self.industry_info = board_info.get('industry_info', {})
                self.concept_info = board_info.get('concept_info', {})
                self.index_info = board_info.get('index_info', {})

                # 记录更新信息
                update_date = board_info.get('update_date', 'unknown')
                update_datetime = board_info.get('update_datetime', 'unknown')
                version = board_info.get('version', 'unknown')

                print("从缓存加载板块数据成功")
                print(f"更新日期: {update_date}")
                print(f"数据版本: {version}")
                print(f"行业板块: {len(self.industry_info)} 个")
                print(f"概念板块: {len(self.concept_info)} 个")
                print(f"指数板块: {len(self.index_info)} 个")

        except Exception as e:
            error_msg = f"加载板块数据缓存失败: {e}\n" \
                       f"缓存文件: {self.BOARD_INFO_CACHE}\n" \
                       f"建议重新更新数据: python -m common.board_data_manager update"
            raise Exception(error_msg)






    def _add_stock_to_graph(self, stock_code: str, stock_name: str,
                           board_node: BoardNode, edge_type: BoardEdgeType) -> None:
        """添加股票到图中"""
        if not stock_code:
            return

        stock_code = StockCodeUtils.extract_clean_code(stock_code)
        stock_node = BoardNode(stock_code, stock_name, BoardNodeType.STOCK)

        # 更新节点索引
        self.stock_nodes[stock_code] = stock_node
        self.stock_nodes[stock_name] = stock_node
        self.stock_code_name_dict[stock_code] = stock_name
        self.stock_name_code_dict[stock_name] = stock_code

        # 添加边关系
        self.graph[board_node][stock_node] = edge_type.value
        if stock_node not in self.graph:
            self.graph[stock_node] = {}
        self.graph[stock_node][board_node] = edge_type.value


    def construct_graph(self) -> None:
        """构建关系图"""
        # 构建行业关系
        for code, info in self.industry_info.items():
            node_type = BoardNodeType.from_int(info['type'])
            node = BoardNode(code, info['name'], node_type)
            self.industry_nodes[code] = node
            self.industry_nodes[info['name']] = node
            self.graph[node] = {}

            # 处理股票数据 - 可能是DataFrame或dict格式
            cons_data = info.get('cons')
            if cons_data is not None:
                if isinstance(cons_data, pd.DataFrame):
                    # DataFrame格式
                    for _, row in cons_data.iterrows():
                        stock_code = DataProcessingUtils.safe_strip(row.get('股票代码', row.get('stock_code', '')))
                        stock_name = DataProcessingUtils.safe_strip(row.get('股票简称', row.get('stock_name', '')))

                        if stock_code and len(stock_code) >= 6:
                            stock_code = stock_code[:6]
                            self._add_stock_to_graph(stock_code, stock_name, node, BoardEdgeType.INDUSTRY_RELATION)

                elif isinstance(cons_data, dict):
                    # 字典格式
                    for stock_code, stock_info in cons_data.items():
                        if isinstance(stock_info, dict):
                            stock_name = stock_info.get('name', '')
                        else:
                            stock_name = str(stock_info)
                        self._add_stock_to_graph(stock_code, stock_name, node, BoardEdgeType.INDUSTRY_RELATION)

        # 构建概念关系
        for code, info in self.concept_info.items():
            node_type = BoardNodeType.from_int(info['type'])
            node = BoardNode(code, info['name'], node_type)
            self.concept_nodes[code] = node
            self.concept_nodes[info['name']] = node
            self.graph[node] = {}

            # 处理股票数据
            cons_data = info.get('cons')
            if cons_data is not None:
                if isinstance(cons_data, pd.DataFrame):
                    # DataFrame格式
                    for _, row in cons_data.iterrows():
                        stock_code = DataProcessingUtils.safe_strip(row.get('股票代码', row.get('代码', '')))
                        stock_name = DataProcessingUtils.safe_strip(row.get('股票简称', row.get('名称', '')))
                        self._add_stock_to_graph(stock_code, stock_name, node, BoardEdgeType.CONCEPT_RELATION)

                elif isinstance(cons_data, dict):
                    # 字典格式
                    for stock_code, stock_info in cons_data.items():
                        if isinstance(stock_info, dict):
                            stock_name = stock_info.get('name', '')
                        else:
                            stock_name = str(stock_info)
                        self._add_stock_to_graph(stock_code, stock_name, node, BoardEdgeType.CONCEPT_RELATION)

        # 构建指数关系
        for code, info in self.index_info.items():
            node_type = BoardNodeType.from_int(info['type'])
            node = BoardNode(code, info['name'], node_type)
            self.index_nodes[code] = node
            self.index_nodes[info['name']] = node
            self.graph[node] = {}

            # 处理股票数据
            cons_data = info.get('cons')
            if cons_data is not None and isinstance(cons_data, dict):
                for stock_code, stock_info in cons_data.items():
                    if isinstance(stock_info, dict):
                        stock_name = stock_info.get('name', '')
                    else:
                        stock_name = str(stock_info)
                    self._add_stock_to_graph(stock_code, stock_name, node, BoardEdgeType.INDEX_RELATION)

    def construct_industry_graph(self, industry_info: Dict[str, Dict]) -> List[Dict]:
        """构建行业板块层次图"""
        # 构建层次结构
        level1_industries = {}

        # 处理一级行业
        for code, info in industry_info.items():
            if info['type'] == BoardNodeType.INDUSTRY_L1.value:
                level1_industries[code] = {
                    "name": info['name'],
                    "code": code,
                    "children": []
                }

        # 处理二级行业
        for code, info in industry_info.items():
            if info['type'] == BoardNodeType.INDUSTRY_L2.value:
                parent_name = info.get('parent_name')
                # 找到父节点
                parent_found = False
                for l1_code, l1_info in level1_industries.items():
                    if l1_info['name'] == parent_name:
                        l1_info['children'].append({
                            "name": info['name'],
                            "code": code,
                            "children": []
                        })
                        parent_found = True
                        break

                if not parent_found:
                    # 如果找不到父节点，创建一个独立的二级行业
                    level1_industries[code] = {
                        "name": info['name'],
                        "code": code,
                        "children": []
                    }

        # 处理三级行业
        for code, info in industry_info.items():
            if info['type'] == BoardNodeType.INDUSTRY_L3.value:
                parent_name = info.get('parent_name')
                # 在所有节点中查找父节点
                parent_found = False

                # 先在一级行业中查找
                for l1_info in level1_industries.values():
                    for l2_info in l1_info['children']:
                        if l2_info['name'] == parent_name:
                            l2_info['children'].append({
                                "name": info['name'],
                                "code": code
                            })
                            parent_found = True
                            break
                    if parent_found:
                        break

                if not parent_found:
                    # 如果找不到父节点，创建一个独立的节点
                    level1_industries[code] = {
                        "name": info['name'],
                        "code": code,
                        "children": []
                    }

        return [{"name": "Industry", "children": list(level1_industries.values())}]

    def construct_concept_graph(self, concept_info: Dict[str, Dict]) -> List[Dict]:
        """构建概念板块图"""
        graph = []
        for code, info in concept_info.items():
            graph.append({
                "name": info['name'],
                "code": code,
                "children": []
            })
        return [{"name": "Concept", "children": graph}]

    def construct_index_graph(self, index_info: Dict[str, Dict]) -> List[Dict]:
        """构建指数板块图"""
        graph = []
        for code, info in index_info.items():
            graph.append({
                "name": info['name'],
                "code": code,
                "children": []
            })
        return [{"name": "Index", "children": graph}]

    def get_stocks_by_industry(self, key: str) -> Optional[List[str]]:
        """
        根据行业板块获取股票代码列表

        Args:
            key: 行业代码或名称

        Returns:
            股票代码列表
        """
        if key in self.industry_nodes:
            industry_node = self.industry_nodes[key]
            stocks = []
            for node, edge_weight in self.graph[industry_node].items():
                if edge_weight == BoardEdgeType.INDUSTRY_RELATION.value and node.node_type == BoardNodeType.STOCK:  # 行业关系且为股票节点
                    stocks.append(node.code)
            return stocks
        return None

    def get_stocks_by_concept(self, key: str) -> Optional[List[str]]:
        """
        根据概念板块获取股票代码列表

        Args:
            key: 概念代码或名称

        Returns:
            股票代码列表
        """
        if key in self.concept_nodes:
            concept_node = self.concept_nodes[key]
            stocks = []
            for node, edge_weight in self.graph[concept_node].items():
                if edge_weight == BoardEdgeType.CONCEPT_RELATION.value and node.node_type == BoardNodeType.STOCK:  # 概念关系且为股票节点
                    stocks.append(node.code)
            return stocks
        return None

    def get_stocks_by_index(self, key: str) -> Optional[List[str]]:
        """
        根据指数板块获取股票代码列表

        Args:
            key: 指数代码或名称

        Returns:
            股票代码列表
        """
        if key in self.index_nodes:
            index_node = self.index_nodes[key]
            stocks = []
            for node, edge_weight in self.graph[index_node].items():
                if edge_weight == BoardEdgeType.INDEX_RELATION.value and node.node_type == BoardNodeType.STOCK:  # 指数关系且为股票节点
                    stocks.append(node.code)
            return stocks
        return None

    def get_concepts_by_stock(self, key: str) -> Optional[List[BoardNode]]:
        """
        根据股票获取所属的概念板块

        Args:
            key: 股票代码或名称

        Returns:
            概念板块节点列表
        """
        if key in self.stock_nodes:
            stock_node = self.stock_nodes[key]
            concepts = []
            for node, edge_weight in self.graph[stock_node].items():
                if edge_weight == BoardEdgeType.CONCEPT_RELATION.value and node.node_type == BoardNodeType.CONCEPT:  # 概念关系且为概念节点
                    concepts.append(node)
            return concepts
        return None

    def get_industries_by_stock(self, key: str) -> Optional[List[BoardNode]]:
        """
        根据股票获取所属的行业板块

        Args:
            key: 股票代码或名称

        Returns:
            行业板块节点列表
        """
        if key in self.stock_nodes:
            stock_node = self.stock_nodes[key]
            industries = []
            for node, edge_weight in self.graph[stock_node].items():
                if edge_weight == BoardEdgeType.INDUSTRY_RELATION.value and node.node_type in BoardNodeType.get_industry_types():  # 行业关系且为行业节点
                    industries.append(node)
            return industries
        return None

    def get_indexes_by_stock(self, key: str) -> Optional[List[BoardNode]]:
        """
        根据股票获取所属的指数板块

        Args:
            key: 股票代码或名称

        Returns:
            指数板块节点列表
        """
        if key in self.stock_nodes:
            stock_node = self.stock_nodes[key]
            indexes = []
            for node, edge_weight in self.graph[stock_node].items():
                if edge_weight == BoardEdgeType.INDEX_RELATION.value and node.node_type == BoardNodeType.INDEX:  # 指数关系且为指数节点
                    indexes.append(node)
            return indexes
        return None

    def collect_board_codes(self, industry_keys: List[str] = None,
                           concept_keys: List[str] = None,
                           stock_codes: List[str] = None,
                           index_keys: List[str] = None) -> List[str]:
        """
        收集多个板块条件下的股票代码

        Args:
            industry_keys: 行业板块键列表
            concept_keys: 概念板块键列表
            stock_codes: 股票代码列表
            index_keys: 指数板块键列表

        Returns:
            股票代码集合
        """
        codes = set()

        # 处理行业板块
        if industry_keys:
            for key in industry_keys:
                board_codes = self.get_stocks_by_industry(key)
                if board_codes:
                    codes.update(board_codes)
                else:
                    raise ValueError(f"行业板块 '{key}' 不存在")

        # 处理概念板块
        if concept_keys:
            for key in concept_keys:
                board_codes = self.get_stocks_by_concept(key)
                if board_codes:
                    codes.update(board_codes)
                else:
                    raise ValueError(f"概念板块 '{key}' 不存在")

        # 处理指数板块
        if index_keys:
            for key in index_keys:
                board_codes = self.get_stocks_by_index(key)
                if board_codes:
                    codes.update(board_codes)
                else:
                    raise ValueError(f"指数板块 '{key}' 不存在")

        # 添加直接指定的股票代码
        if stock_codes:
            codes.update(stock_codes)

        return list(codes)

    def get_node(self, key: str, board_type: str) -> Optional[BoardNode]:
        """
        根据键和类型获取节点

        Args:
            key: 节点键（代码或名称）
            board_type: 板块类型 ('industry', 'concept', 'index')

        Returns:
            节点对象
        """
        if board_type == "industry":
            return self.industry_nodes.get(key)
        elif board_type == "concept":
            return self.concept_nodes.get(key)
        elif board_type == "index":
            return self.index_nodes.get(key)
        else:
            raise ValueError(f"不支持的板块类型: {board_type}")

    def get_stock_name(self, code: str) -> Optional[str]:
        """根据股票代码获取股票名称"""
        return self.stock_code_name_dict.get(code)

    def get_stock_code(self, name: str) -> Optional[str]:
        """根据股票名称获取股票代码"""
        return self.stock_name_code_dict.get(name)


if __name__ == "__main__":
    # 测试示例
    try:
        board_graph = BoardGraph()

        # 测试获取股票所属板块
        test_stock = "000001"  # 平安银行
        industries = board_graph.get_industries_by_stock(test_stock)
        concepts = board_graph.get_concepts_by_stock(test_stock)

        print(f"股票 {test_stock} 所属行业:")
        if industries:
            for industry in industries[:3]:  # 只显示前3个
                print(f"  - {industry.name} ({industry.code})")

        print(f"股票 {test_stock} 所属概念:")
        if concepts:
            for concept in concepts[:3]:  # 只显示前3个
                print(f"  - {concept.name} ({concept.code})")

        # 测试获取板块内股票
        industry_stocks = board_graph.get_stocks_by_industry("银行")
        if industry_stocks:
            print(f"银行行业内股票数量: {len(industry_stocks)}")
            print(f"前5只股票: {industry_stocks[:5]}")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()