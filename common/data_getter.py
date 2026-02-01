"""
数据获取模块 - 重构版本
整合个股基本信息和行情数据获取功能
"""

import os
import math
import datetime
import pickle
import pandas as pd
import numpy as np
import akshare as ak
from pathlib import Path
from datetime import timedelta
from typing import List, Dict, Union, Optional, Any

# 导入自定义模块
try:
    from .logger_utils import logger
except ImportError:
    # 如果logger_utils不存在，创建简单的logger
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from .board_graph import BoardGraph
    from .trade_date import TradeDate
except ImportError:
    # 如果这些模块不存在，暂时设为None
    BoardGraph = None
    TradeDate = None


# 数据字段定义
class DataFields:
    """数据字段定义"""

    # 个股基本信息字段
    STOCK_BASIC_REQUIRED = ['code', 'name']  # 必选字段
    STOCK_BASIC_OPTIONAL = ['total_mv', 'cir_mv', 'pe', 'pb', 'total_shares', 'cir_shares']  # 可选字段
    STOCK_BASIC_ALL = STOCK_BASIC_REQUIRED + STOCK_BASIC_OPTIONAL

    # 行情数据字段
    MARKET_DATA_REQUIRED = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pre_close']
    MARKET_DATA_OPTIONAL = ['open_interest', 'suspend_flag']  # 可选字段
    MARKET_DATA_ALL = MARKET_DATA_REQUIRED + MARKET_DATA_OPTIONAL


class DataGetter:
    """数据获取类 - 重构版本
    整合个股基本信息和行情数据获取功能
    """

    def __init__(self, xtdata_dir: str = r'G:\国金证券QMT交易端\datadir'):
        """初始化数据获取器

        Args:
            xtdata_dir: xtdata数据目录路径
        """
        try:
            from xtquant import xtdata
            # 配置xtdata数据目录
            xtdata.data_dir = xtdata_dir
            # 禁用问候语
            xtdata.enable_hello = False
            self.xtdata = xtdata
        except ImportError:
            logger.warning("xtquant未安装，将使用模拟模式")
            self.xtdata = None

        # 初始化相关对象
        self.board_graph = self._init_board_graph()
        self.trade_date = self._init_trade_date()

        # 缓存目录
        self.cache_base_dir = Path("/tmp/cache_output/quantara/data_getter")
        self.cache_base_dir.mkdir(parents=True, exist_ok=True)

        # 个股基本信息缓存
        self._stock_basic_cache = None
        self._stock_basic_cache_time = None
        self._cache_expire_hours = 24  # 缓存过期时间（小时）

    def _init_board_graph(self):
        """初始化板块图对象"""
        if BoardGraph is None:
            return None
        try:
            return BoardGraph()
        except Exception as e:
            logger.warning(f"初始化BoardGraph失败: {e}")
            return None

    def _init_trade_date(self):
        """初始化交易日期对象"""
        if TradeDate is None:
            return None
        try:
            return TradeDate()
        except Exception as e:
            logger.warning(f"初始化TradeDate失败: {e}")
            return None

    @property
    def name(self) -> str:
        """获取数据获取器名称"""
        return "DataGetter"

    @staticmethod
    def transform_code(code: str) -> str:
        """转换股票代码格式为6位数字格式

        支持的输入格式：
        - '000001.SH' -> '000001'
        - 'SH000001' -> '000001'
        - '000001sh' -> '000001'
        - 'sh000001' -> '000001'
        - '000001' -> '000001' (已有6位数字格式)

        Args:
            code: 股票代码，支持多种输入格式

        Returns:
            6位数字格式的股票代码，如'000001'
        """
        import re

        # 移除所有空白字符
        code = code.strip()

        # 如果已经是6位数字，直接返回
        if re.match(r'^\d{6}$', code):
            return code

        # 匹配格式1: XXXXXX.SH 或 XXXXXX.SZ 或 XXXXXX.BJ
        match1 = re.match(r'^(\d{6})\.([A-Z]{2})$', code)
        if match1:
            return match1.group(1)

        # 匹配格式2: SHXXXXXX 或 SZXXXXXX 或 BJXXXXXX (大写)
        match2 = re.match(r'^([A-Z]{2})(\d{6})$', code)
        if match2:
            return match2.group(2)

        # 匹配格式3: XXXXXXsh 或 XXXXXXsz 或 XXXXXXbj (小写)
        match3 = re.match(r'^(\d{6})([a-z]{2})$', code)
        if match3:
            return match3.group(1)

        # 匹配格式4: shXXXXXX 或 szXXXXXX 或 bjXXXXXX (小写)
        match4 = re.match(r'^([a-z]{2})(\d{6})$', code)
        if match4:
            return match4.group(2)

        # 如果都不匹配，抛出错误
        raise ValueError(f"无效的股票代码格式: {code}，支持格式: '000001.SH', 'SH000001', '000001sh', 'sh000001'")

    @staticmethod
    def transform_code_for_xtdata(code: str) -> str:
        """转换股票代码格式为xtdata所需格式

        Args:
            code: 6位数字格式的股票代码

        Returns:
            xtdata所需的格式，如'000001.SZ'
        """
        # 首先转换为6位数字格式
        clean_code = DataGetter.transform_code(code)

        # 根据规则添加交易所后缀
        if clean_code.startswith(('6', '5')):
            return f"{clean_code}.SH"
        elif clean_code.startswith(('0', '3', '1')):
            return f"{clean_code}.SZ"
        elif clean_code.startswith(('8', '9', '4')):
            return f"{clean_code}.BJ"
        else:
            raise ValueError(f"无法确定交易所: {clean_code}")

    def _get_cache_file_path(self, cache_type: str, identifier: str, date_str: str = None) -> Path:
        """获取缓存文件路径

        Args:
            cache_type: 缓存类型 ('stock_basic', 'market_data', 'sector_info')
            identifier: 标识符（如股票代码、周期等）
            date_str: 日期字符串（可选）

        Returns:
            缓存文件路径
        """
        if date_str:
            sub_dir = self.cache_base_dir / date_str
        else:
            sub_dir = self.cache_base_dir

        sub_dir.mkdir(parents=True, exist_ok=True)
        return sub_dir / f"{cache_type}_{identifier}.pkl"

    def _load_from_cache(self, cache_file: Path) -> Optional[Any]:
        """从缓存加载数据

        Args:
            cache_file: 缓存文件路径

        Returns:
            缓存的数据，如果不存在或过期则返回None
        """
        if not cache_file.exists():
            return None

        # 检查文件是否过期（24小时）
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > timedelta(hours=self._cache_expire_hours):
            cache_file.unlink()  # 删除过期文件
            return None

        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"读取缓存文件失败 {cache_file}: {e}")
            return None

    def _save_to_cache(self, cache_file: Path, data: Any):
        """保存数据到缓存

        Args:
            cache_file: 缓存文件路径
            data: 要缓存的数据
        """
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.warning(f"保存缓存文件失败 {cache_file}: {e}")

    def get_stock_basic_info(self, codes: Union[str, List[str]] = None,
                           refresh: bool = False) -> pd.DataFrame:
        """获取个股基本信息

        Args:
            codes: 股票代码列表，如果为None则获取全部A股数据
            refresh: 是否强制刷新缓存

        Returns:
            包含个股基本信息的DataFrame，字段包括：
            - code: 个股代码（必选）
            - name: 个股名称（必选）
            - total_mv: 总市值（可选）
            - cir_mv: 流通市值（可选）
            - pe: 市盈率（可选）
            - pb: 市净率（可选）
            - total_shares: 总股本（可选）
            - cir_shares: 流通股本（可选）
        """
        cache_file = self._get_cache_file_path('stock_basic', 'all_stocks')

        # 检查缓存（除非强制刷新）
        if not refresh:
            cached_data = self._load_from_cache(cache_file)
            if cached_data is not None:
                logger.info("从缓存加载个股基本信息")
                # 如果指定了特定代码，则过滤数据
                if codes is not None:
                    code_list = [codes] if isinstance(codes, str) else codes
                    # 转换输入代码为6位数字格式
                    clean_code_list = [self.transform_code(code) for code in code_list]
                    mask = cached_data['code'].isin(clean_code_list)
                    return cached_data[mask].copy()
                return cached_data

        # 从akshare获取数据
        logger.info("从akshare获取个股基本信息")
        try:
            # 获取A股实时行情数据
            raw_data = ak.stock_zh_a_spot_em()

            # 转换数据格式
            stock_data = []
            for _, row in raw_data.iterrows():
                stock_info = {
                    'code': str(row['代码']),
                    'name': str(row['名称']),
                    'total_mv': float(row['总市值']) if pd.notna(row['总市值']) else None,
                    'cir_mv': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                    'pe': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                    'pb': float(row['市净率']) if pd.notna(row['市净率']) else None,
                    # 总股本和流通股本暂时设为None，后续可通过其他接口获取
                    'total_shares': None,
                    'cir_shares': None
                }
                stock_data.append(stock_info)

            # 创建DataFrame
            df = pd.DataFrame(stock_data)

            # 设置数据类型
            df['code'] = df['code'].astype(str)
            df['name'] = df['name'].astype(str)

            # 保存到缓存
            self._save_to_cache(cache_file, df)
            logger.info(f"成功获取并缓存 {len(df)} 只股票的基本信息")

            # 如果指定了特定代码，则过滤数据
            if codes is not None:
                code_list = [codes] if isinstance(codes, str) else codes
                # 转换输入代码为6位数字格式
                clean_code_list = [self.transform_code(code) for code in code_list]
                mask = df['code'].isin(clean_code_list)
                return df[mask].copy()

            return df

        except Exception as e:
            logger.error(f"获取个股基本信息失败: {e}")
            # 如果有缓存数据，即使过期也返回
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        return pickle.load(f)
                except:
                    pass
            raise

    def get_market_data(self, codes: Union[str, List[str]], period: str = '1d',
                       count: int = 1000, refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """获取历史行情数据

        Args:
            codes: 股票代码列表
            period: 周期，'1d'/'1m'/'5m'
            count: 获取的K线数量
            refresh: 是否强制刷新缓存

        Returns:
            数据字典，key为股票代码，value为行情数据DataFrame
            DataFrame字段包括：
            - datetime: 时间（索引）
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交额
            - pre_close: 前收盘价
        """
        # 参数验证
        if period not in ['1d', '1m', '5m']:
            raise ValueError(f"不支持的周期: {period}，只支持 '1d', '1m', '5m'")
        if count <= 0:
            raise ValueError(f"count必须大于0，当前值: {count}")
        if self.xtdata is None:
            raise RuntimeError("xtquant未安装，无法获取行情数据")

        code_list = [codes] if isinstance(codes, str) else codes

        # 转换代码格式为6位数字，并创建映射
        clean_code_list = [self.transform_code(code) for code in code_list]
        code_mapping = dict(zip(code_list, clean_code_list))  # 原始代码 -> 清洁代码

        result = {}

        # 获取当前日期
        today = datetime.datetime.now().date()
        today_str = today.strftime("%Y%m%d")

        # 处理每个股票代码
        for original_code, clean_code in zip(code_list, clean_code_list):
            cache_file = self._get_cache_file_path('market_data', f"{clean_code}_{period}_{count}", today_str)

            # 检查缓存（除非强制刷新）
            if not refresh:
                cached_data = self._load_from_cache(cache_file)
                if cached_data is not None:
                    logger.info(f"从缓存加载股票 {original_code} 的 {period} 周期 {count} 根K线数据")
                    result[original_code] = cached_data
                    continue

            # 从xtdata获取数据
            try:
                data = self._fetch_market_data_from_xtdata(clean_code, period, count)
                if data is not None and len(data) >= count:
                    # 数据足够，保存到缓存并返回
                    self._save_to_cache(cache_file, data)
                    logger.info(f"成功获取并缓存股票 {original_code} 的 {period} 周期 {count} 根K线数据")
                    result[original_code] = data
                    continue
                else:
                    logger.warning(f"xtdata返回的数据不足，股票 {original_code}，期望 {count} 根，实际 {len(data) if data is not None else 0} 根")
            except Exception as e:
                logger.warning(f"从xtdata获取股票 {original_code} 数据失败: {e}")

            # 如果获取失败，返回None
            result[original_code] = None

        return result if len(result) > 1 or isinstance(codes, list) else list(result.values())[0]

    def _fetch_market_data_from_xtdata(self, code: str, period: str, count: int) -> Optional[pd.DataFrame]:
        """从xtdata获取指定数量的历史数据

        Args:
            code: 股票代码，如 '600000'
            period: 周期，'1d'/'1m'/'5m'
            count: K线数量

        Returns:
            DataFrame: 历史数据
        """
        # 计算时间范围
        end_date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

        if period == '1d':
            # 日线数据，估算需要的天数
            days_needed = count * 2  # 多取一些确保够数
            start_date = end_date - timedelta(days=days_needed)
        else:
            start_date = end_date - timedelta(days=20)

        # 转换格式
        if period.endswith('m'):
            start_dt_str = start_date.strftime("%Y%m%d%H%M%S")
            end_dt_str = end_date.strftime("%Y%m%d%H%M%S")
        else:
            start_dt_str = start_date.strftime("%Y%m%d")
            end_dt_str = end_date.strftime("%Y%m%d")

        # 获取数据
        trans_code = self.transform_code_for_xtdata(code)
        data_dict = self.xtdata.get_market_data_ex(
            field_list=[],
            stock_list=[trans_code],
            period=period,
            start_time=start_dt_str,
            end_time=end_dt_str
        )

        # 处理数据
        if trans_code in data_dict and data_dict[trans_code] is not None:
            df = self._transform_market_data(data_dict[trans_code], period)
            # 取最新的count根K线
            if len(df) > count:
                df = df.tail(count)
            return df

        return None

    def _transform_market_data(self, raw_df: pd.DataFrame, period: str) -> pd.DataFrame:
        """转换原始行情数据格式

        Args:
            raw_df: 原始数据DataFrame
            period: 周期

        Returns:
            转换后的数据DataFrame
        """
        raw_df = raw_df.copy()
        raw_df.index = pd.to_datetime(raw_df.index)

        # 检查原始数据的列数
        raw_cols = len(raw_df.columns)

        if period == '1d':
            # 日K线数据格式转换
            if raw_cols >= 10:
                df = raw_df.copy()
                df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount',
                            'open_interest', 'pre_close', 'suspend_flag'][:raw_cols]
                # 删除多余的列，只保留必需字段
                keep_cols = ['datetime'] + DataFields.MARKET_DATA_REQUIRED[1:]  # 除去datetime
                df = df[keep_cols] if all(col in df.columns for col in keep_cols) else df
            else:
                logger.warning(f"日K线数据列数异常: {raw_cols}")
                return raw_df
        else:
            # 分钟线数据格式转换
            if raw_cols >= 10:
                df = raw_df.copy()
                df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount',
                            'open_interest', 'pre_close', 'suspend_flag'][:raw_cols]
                # 删除多余的列，只保留必需字段
                keep_cols = ['datetime'] + DataFields.MARKET_DATA_REQUIRED[1:]  # 除去datetime
                df = df[keep_cols] if all(col in df.columns for col in keep_cols) else df
            else:
                logger.warning(f"分钟线数据列数异常: {raw_cols}")
                return raw_df

        # 数据类型转换
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pre_close']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 设置datetime为索引
        if 'datetime' in df.columns:
            df.set_index('datetime', inplace=True)

        return df

    def get_real_time_data(self, codes: Union[str, List[str]]) -> Union[Dict[str, pd.DataFrame], pd.DataFrame]:
        """获取实时行情数据

        Args:
            codes: 股票代码列表或单个代码

        Returns:
            实时行情数据字典或DataFrame
        """
        if self.xtdata is None:
            raise RuntimeError("xtquant未安装，无法获取实时数据")

        code_list = [codes] if isinstance(codes, str) else codes

        # 转换代码格式并创建映射
        clean_code_list = [self.transform_code(code) for code in code_list]
        trans_code_list = [self.transform_code_for_xtdata(clean_code) for clean_code in clean_code_list]
        code_mapping = dict(zip(trans_code_list, code_list))  # xtdata格式 -> 原始格式

        # 调用xtdata.get_full_tick接口获取实时数据
        real_data = self.xtdata.get_full_tick(trans_code_list)

        # 转换数据格式
        result = {}
        if real_data is not None:
            for trans_code, tick_data in real_data.items():
                original_code = code_mapping[trans_code]

                # 转换tick数据为标准格式
                standardized_data = {
                    'datetime': tick_data.get('datetime', tick_data.get('time', None)),
                    'open': tick_data.get('open', tick_data.get('openPrice', 0)),
                    'high': tick_data.get('high', tick_data.get('highPrice', 0)),
                    'low': tick_data.get('low', tick_data.get('lowPrice', 0)),
                    'close': tick_data.get('lastPrice', tick_data.get('price', 0)),
                    'volume': tick_data.get('volume', tick_data.get('qty', 0)),
                    'amount': tick_data.get('amount', tick_data.get('turnover', 0)),
                    'pre_close': tick_data.get('lastClose', tick_data.get('preClose', 0))
                }

                # 创建单行DataFrame
                df = pd.DataFrame([standardized_data])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)

                result[original_code] = df

        return result if len(result) > 1 or isinstance(codes, list) else list(result.values())[0] if result else None

    def get_stock_sector_info(self, codes: Union[str, List[str]]) -> Union[Dict[str, Dict], Dict]:
        """获取个股板块信息

        Args:
            codes: 股票代码列表或单个代码

        Returns:
            板块信息字典
        """
        if self.board_graph is None:
            logger.warning("BoardGraph未初始化，无法获取板块信息")
            return {}

        code_list = [codes] if isinstance(codes, str) else codes

        # 转换代码格式为6位数字，并创建映射
        clean_code_list = [self.transform_code(code) for code in code_list]
        code_mapping = dict(zip(clean_code_list, code_list))  # 清洁代码 -> 原始代码

        # 初始化结果字典（使用原始输入格式作为key）
        sector_info = {}
        for original_code in code_list:
            sector_info[original_code] = {
                'industry': [],
                'concept': [],
                'index': []
            }

        try:
            logger.info("使用BoardGraph获取板块信息")

            for clean_code, original_code in zip(clean_code_list, code_list):
                # 获取行业板块
                industrys = self.board_graph.get_industrys_by_stock(clean_code)
                if industrys:
                    sector_info[original_code]['industry'] = [{
                        'code': ind_node[0],
                        'name': ind_node[1],
                        'sub_type': ind_node[2],
                        'type': 'industry'
                    } for ind_node in industrys]

                # 获取概念板块
                concepts = self.board_graph.get_concepts_by_stock(clean_code)
                if concepts:
                    sector_info[original_code]['concept'] = [{
                        'code': con_node[0],
                        'name': con_node[1],
                        'sub_type': con_node[2],
                        'type': 'concept'
                    } for con_node in concepts]

                # 获取指数板块
                indexs = self.board_graph.get_indexs_by_stock(clean_code)
                if indexs:
                    sector_info[original_code]['index'] = [{
                        'code': idx_node[0],
                        'name': idx_node[1],
                        'sub_type': idx_node[2],
                        'type': 'index'
                    } for idx_node in indexs]

                logger.debug(f"股票 {original_code} 的板块信息: {sector_info[original_code]}")

        except Exception as e:
            logger.error(f"获取板块信息时出错: {e}")

        return sector_info if len(sector_info) > 1 or isinstance(codes, list) else list(sector_info.values())[0]

    def get_latest_trading_day_market_data(self, codes: Union[str, List[str]],
                                          period: str = '1m') -> Union[Dict[str, pd.DataFrame], pd.DataFrame]:
        """获取最新交易日所有K线数据

        Args:
            codes: 股票代码列表
            period: 周期，默认为'1m'

        Returns:
            数据字典或DataFrame
        """
        if self.xtdata is None:
            raise RuntimeError("xtquant未安装，无法获取数据")
        if self.trade_date is None:
            raise RuntimeError("TradeDate未初始化，无法获取最新交易日")

        # 获取最新的交易日
        today = datetime.datetime.now().date()

        # 从今天开始向前查找最近的交易日
        latest_trading_day = None
        for i in range(7):  # 检查最近7天
            check_date = today - datetime.timedelta(days=i)
            if self.trade_date.is_trade_date(check_date):
                latest_trading_day = check_date
                break

        if latest_trading_day is None:
            logger.error("无法找到最近的交易日")
            return None

        logger.info(f"获取最新交易日: {latest_trading_day}")

        # 设置交易日的开始时间
        start_time = datetime.datetime.combine(latest_trading_day, datetime.time(9, 30, 0))

        # 设置交易日的结束时间
        now = datetime.datetime.now()

        # 如果今天是交易日且当前时间在交易时间内，使用当前时间作为结束时间
        if latest_trading_day == today:
            current_time = now.time()
            trading_start = datetime.time(9, 30, 0)
            trading_end = datetime.time(15, 0, 0)

            if trading_start <= current_time <= trading_end:
                # 在盘中，使用当前时间
                end_time = now
                logger.info(f"当前在盘中，结束时间设置为当前时间: {end_time}")
            else:
                # 不在交易时间，使用收盘时间
                end_time = datetime.datetime.combine(latest_trading_day, datetime.time(15, 0, 0))
                logger.info(f"当前不在交易时间，结束时间设置为收盘时间: {end_time}")
        else:
            # 昨天或更早的交易日，使用收盘时间
            end_time = datetime.datetime.combine(latest_trading_day, datetime.time(15, 0, 0))
            logger.info(f"获取历史交易日数据，结束时间设置为收盘时间: {end_time}")

        # 转换时间格式
        start_time_str = start_time.strftime("%Y%m%d%H%M%S")
        end_time_str = end_time.strftime("%Y%m%d%H%M%S")

        # 转换股票代码格式
        code_list = [codes] if isinstance(codes, str) else codes

        # 转换代码格式并创建映射
        clean_code_list = [self.transform_code(code) for code in code_list]
        trans_code_list = [self.transform_code_for_xtdata(clean_code) for clean_code in clean_code_list]
        code_mapping = dict(zip(trans_code_list, code_list))  # xtdata格式 -> 原始格式

        # 调用xtdata.get_full_kline接口
        try:
            data_dict = self.xtdata.get_full_kline(
                field_list=[],
                stock_list=trans_code_list,
                period=period,
                start_time=start_time_str,
                end_time=end_time_str,
                dividend_type='none',
                fill_data=True
            )

            if data_dict is None:
                logger.warning("xtdata.get_full_kline返回None")
                return None

            # 处理数据格式转换
            result = {}
            for trans_code, raw_df in data_dict.items():
                if raw_df is not None and len(raw_df) > 0:
                    # 转换为标准格式
                    df = self._transform_market_data(raw_df, period)
                    # 获取原始代码格式
                    original_code = code_mapping[trans_code]
                    result[original_code] = df
                else:
                    logger.warning(f"股票 {trans_code} 没有数据")

            logger.info(f"成功获取 {len(result)} 只股票的最新交易日K线数据")
            return result if len(result) > 1 or isinstance(codes, list) else list(result.values())[0] if result else None

        except Exception as e:
            logger.error(f"获取最新交易日K线数据失败: {e}")

            # 检查是否是客户端不支持的错误，如果是则回退到普通的历史数据获取
            error_str = str(e)
            if "function not realize" in error_str or "ErrorID" in error_str:
                logger.info("检测到客户端不支持get_full_kline，回退到使用get_history_data方法")

                try:
                    # 使用现有的get_history_data方法作为回退
                    # 对于日线，获取最近1天的完整数据
                    # 对于分钟线，获取最近交易日的完整分钟数据（通常是240根1分钟K线）
                    if period == '1d':
                        fallback_count = 1  # 1天日线
                    elif period == '1m':
                        fallback_count = 240  # 交易日通常4小时 = 240分钟
                    else:  # 5m
                        fallback_count = 48   # 交易日通常4小时 = 48根5分钟K线

                    logger.info(f"尝试通过get_market_data获取最近{fallback_count}根{period}K线作为回退")
                    fallback_data = self.get_market_data(codes, period=period, count=fallback_count)

                    if fallback_data is not None:
                        logger.info("成功通过回退方法获取数据")
                        return fallback_data
                    else:
                        logger.warning("回退方法未能获取数据")
                except Exception as fallback_e:
                    logger.error(f"回退方法执行失败: {fallback_e}")

            return None

    def clear_cache(self, cache_type: str = None, older_than_hours: int = None):
        """清理缓存文件

        Args:
            cache_type: 缓存类型，如果为None则清理所有类型
            older_than_hours: 清理多少小时之前的文件，如果为None则清理所有文件
        """
        if older_than_hours is None:
            # 删除所有缓存文件
            if cache_type:
                for file_path in self.cache_base_dir.glob(f"{cache_type}_*.pkl"):
                    file_path.unlink()
                for sub_dir in self.cache_base_dir.iterdir():
                    if sub_dir.is_dir():
                        for file_path in sub_dir.glob(f"{cache_type}_*.pkl"):
                            file_path.unlink()
            else:
                import shutil
                shutil.rmtree(self.cache_base_dir)
                self.cache_base_dir.mkdir(parents=True, exist_ok=True)
        else:
            # 删除过期文件
            cutoff_time = datetime.datetime.now() - timedelta(hours=older_than_hours)
            for file_path in self.cache_base_dir.rglob("*.pkl"):
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    if cache_type is None or cache_type in file_path.name:
                        file_path.unlink()

        logger.info("缓存清理完成")


# 为了向后兼容，提供别名
StockBasicInfo = DataGetter


if __name__ == "__main__":
    # 使用示例
    getter = DataGetter()

    # 获取个股基本信息
    print("获取个股基本信息示例:")
    basic_info = getter.get_stock_basic_info(['000001', '600000'])
    print(basic_info.head() if basic_info is not None else "无数据")

    # 获取行情数据
    print("\n获取行情数据示例:")
    market_data = getter.get_market_data('000001', period='1d', count=10)
    print(market_data.head() if market_data is not None else "无数据")