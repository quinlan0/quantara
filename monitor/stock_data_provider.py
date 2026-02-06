#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据提供模块

支持两种模式获取股票数据：
1. 文件模式 (file)：从指定路径读取pkl文件
2. 在线模式 (online)：通过DataGetter获取历史行情和基本信息
"""

import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    """
    单个股票的数据接口

    所有字段均为 optional，支持数据缺失的情况
    """
    code: str
    name: Optional[str] = None
    prev_close: Optional[float] = None  # 前一日收盘价
    history_df: Optional[pd.DataFrame] = None  # 历史行情数据 DataFrame

    def has_history(self) -> bool:
        """判断是否有历史数据"""
        return self.history_df is not None and not self.history_df.empty

    def get_prev_close(self, default: Optional[float] = None) -> Optional[float]:
        """
        获取前一日收盘价

        优先使用 prev_close 字段，如果没有则尝试从 history_df 中获取
        """
        if self.prev_close is not None:
            return self.prev_close
        if self.has_history():
            try:
                return float(self.history_df.iloc[-1]['close'])
            except (KeyError, IndexError, TypeError):
                pass
        return default

    def get_name(self, default: str = '') -> str:
        """获取股票名称，如果没有则返回默认值"""
        return self.name if self.name else default


class StockDataProvider:
    """
    股票数据提供者

    支持两种模式：
    - MODE_FILE: 从指定路径读取pkl文件
    - MODE_ONLINE: 通过DataGetter获取数据
    """

    MODE_FILE = 'file'
    MODE_ONLINE = 'online'

    def __init__(
        self,
        mode: str = MODE_FILE,
        data_getter=None,
        file_path: Optional[Union[str, Path]] = None,
        history_count: int = 100,
    ):
        """
        初始化数据提供者

        Args:
            mode: 数据获取模式，'file' 或 'online'
            data_getter: DataGetter 实例（在线模式需要）
            file_path: pkl文件路径（文件模式需要）
            history_count: 在线模式获取的历史K线数量
        """
        self.mode = mode
        self.data_getter = data_getter
        self.file_path = Path(file_path) if file_path else None
        self.history_count = history_count

        # 数据缓存
        self._data_cache: Dict[str, StockData] = {}
        self._raw_data: Dict = {}  # 原始数据缓存（用于文件模式）

    def load_data(self, stock_codes: Optional[List[str]] = None) -> bool:
        """
        加载数据

        Args:
            stock_codes: 股票代码列表，如果为 None 则加载全部（仅文件模式支持）

        Returns:
            是否加载成功
        """
        try:
            if self.mode == self.MODE_FILE:
                return self._load_from_file(stock_codes)
            else:
                return self._load_from_online(stock_codes)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return False

    def _load_from_file(self, stock_codes: Optional[List[str]] = None) -> bool:
        """
        从文件加载数据

        Args:
            stock_codes: 股票代码列表，用于过滤

        Returns:
            是否加载成功
        """
        if self.file_path is None:
            logger.error("文件模式下必须指定 file_path")
            return False

        if not self.file_path.exists():
            logger.error(f"数据文件不存在: {self.file_path}")
            return False

        try:
            from common.utils import load_data
            self._raw_data = load_data(self.file_path)

            if not self._raw_data:
                logger.warning("加载的数据为空")
                return False

            # 转换为 StockData 格式
            codes_to_load = stock_codes if stock_codes else list(self._raw_data.keys())

            for code in codes_to_load:
                if code not in self._raw_data:
                    logger.warning(f"文件中没有股票 {code} 的数据")
                    continue

                stock_info = self._raw_data[code]
                self._data_cache[code] = self._parse_file_stock_data(code, stock_info)

            logger.info(f"从文件加载了 {len(self._data_cache)} 只股票的数据")
            return True

        except Exception as e:
            logger.error(f"从文件加载数据失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _parse_file_stock_data(self, code: str, stock_info: Dict) -> StockData:
        """
        解析文件中的股票数据

        Args:
            code: 股票代码
            stock_info: 原始数据字典

        Returns:
            StockData 实例
        """
        name = None
        prev_close = None
        history_df = None

        try:
            # 获取基本信息
            base_info = stock_info.get('base_info', {})
            name = base_info.get('name')

            # 获取历史数据
            feat = stock_info.get('feat')
            if feat is not None and isinstance(feat, pd.DataFrame) and not feat.empty:
                history_df = feat
                # 从历史数据获取前一日收盘价
                prev_close = float(history_df.iloc[-1]['close'])
        except Exception as e:
            logger.warning(f"解析股票 {code} 数据时出错: {e}")

        return StockData(
            code=code,
            name=name,
            prev_close=prev_close,
            history_df=history_df,
        )

    def _load_from_online(self, stock_codes: Optional[List[str]] = None) -> bool:
        """
        从在线接口加载数据

        Args:
            stock_codes: 股票代码列表（必须提供）

        Returns:
            是否加载成功
        """
        if self.data_getter is None:
            logger.error("在线模式下必须提供 data_getter")
            return False

        if not stock_codes:
            logger.error("在线模式必须指定股票代码列表")
            return False

        try:
            # 获取股票基本信息
            basic_info_df = None
            try:
                basic_info_df = self.data_getter.get_stock_basic_info(stock_codes)
                logger.info(f"获取到 {len(basic_info_df)} 只股票的基本信息")
            except Exception as e:
                logger.warning(f"获取股票基本信息失败: {e}")

            # 获取历史行情数据
            market_data = None
            try:
                market_data = self.data_getter.get_market_data(
                    stock_codes,
                    period='1d',
                    count=self.history_count,
                )
                if isinstance(market_data, pd.DataFrame):
                    # 单个股票返回的是 DataFrame，转换为 dict
                    market_data = {stock_codes[0]: market_data}
                logger.info(f"获取到 {len(market_data) if market_data else 0} 只股票的历史行情")
            except Exception as e:
                logger.warning(f"获取历史行情数据失败: {e}")

            # 组装 StockData
            for code in stock_codes:
                name = None
                prev_close = None
                history_df = None

                # 从基本信息获取名称
                if basic_info_df is not None and not basic_info_df.empty:
                    try:
                        # 尝试多种匹配方式
                        clean_code = code[:6] if len(code) > 6 else code
                        mask = basic_info_df['code'].astype(str).str.contains(clean_code)
                        matched = basic_info_df[mask]
                        if not matched.empty:
                            name = matched.iloc[0].get('name')
                    except Exception:
                        pass

                # 从历史行情获取数据
                if market_data and code in market_data:
                    df = market_data[code]
                    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                        history_df = df
                        # 获取前一日收盘价
                        try:
                            prev_close = float(df.iloc[-1]['close'])
                        except (KeyError, IndexError, TypeError):
                            pass

                self._data_cache[code] = StockData(
                    code=code,
                    name=name,
                    prev_close=prev_close,
                    history_df=history_df,
                )

            logger.info(f"在线模式加载了 {len(self._data_cache)} 只股票的数据")
            return True

        except Exception as e:
            logger.error(f"在线模式加载数据失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def get_stock_data(self, code: str) -> Optional[StockData]:
        """
        获取单个股票的数据

        Args:
            code: 股票代码

        Returns:
            StockData 实例，如果没有则返回 None
        """
        return self._data_cache.get(code)

    def get_all_codes(self) -> List[str]:
        """获取所有已加载的股票代码"""
        return list(self._data_cache.keys())

    def has_data(self, code: str) -> bool:
        """判断是否有某只股票的数据"""
        return code in self._data_cache

    def clear_cache(self):
        """清除缓存"""
        self._data_cache.clear()
        self._raw_data.clear()
