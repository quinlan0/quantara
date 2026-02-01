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
from .utils import StockCodeUtils

# logger将在需要时延迟初始化
def _get_logger():
    """获取logger，延迟初始化"""
    try:
        from .logger import get_logger
        return get_logger()
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)

logger = _get_logger()

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
        # 初始化日志
        if hasattr(logger, 'init_logger'):
            logger.init_logger("data_getter")

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

    def transform_code(self, code: str) -> str:
        """转换股票代码格式为6位数字格式

        Args:
            code: 输入的股票代码

        Returns:
            6位数字格式的股票代码
        """
        return StockCodeUtils.transform_code(code)


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

        只从缓存读取数据，缓存路径：/tmp/cache_output/quantara/date_info/stock_basic_info.pkl

        Args:
            codes: 股票代码列表，如果为None则返回全部A股数据
            refresh: 此参数已废弃，仅为向后兼容保留

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
        from pathlib import Path
        import pickle

        # 指定的缓存路径
        cache_file = Path("/tmp/cache_output/quantara/date_info/stock_basic_info.pkl")

        # 检查缓存文件是否存在
        if not cache_file.exists():
            error_msg = f"股票基本信息缓存文件不存在: {cache_file}\n" \
                       f"请先运行以下命令更新数据:\n" \
                       f"  python -m common.stock_basic_info_manager update"
            raise FileNotFoundError(error_msg)

        try:
            # 从缓存加载数据
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)

            stock_data = cache_data.get('stock_data', [])
            if not stock_data:
                raise ValueError("缓存文件中没有股票数据")

            # 转换为DataFrame
            df = pd.DataFrame(stock_data)

            # 记录加载信息
            update_date = cache_data.get('update_date', 'unknown')
            total_count = cache_data.get('total_count', 0)
            logger.info(f"从缓存加载股票基本信息: {total_count} 只股票，更新日期: {update_date}")

            # 如果指定了特定代码，则过滤数据
            if codes is not None:
                code_list = [codes] if isinstance(codes, str) else codes
                # 转换输入代码为6位数字格式
                clean_code_list = StockCodeUtils.normalize_stock_codes(code_list)
                mask = df['code'].isin(clean_code_list)
                filtered_df = df[mask].copy()
                logger.info(f"过滤出 {len(filtered_df)} 只指定股票")
                return filtered_df

            return df

        except Exception as e:
            error_msg = f"加载股票基本信息缓存失败: {e}\n" \
                       f"缓存文件: {cache_file}\n" \
                       f"建议重新更新数据: python -m common.stock_basic_info_manager update"
            raise Exception(error_msg)

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

            # xtdata获取失败或数据不足，下载数据
            try:
                logger.info(f"开始下载股票 {original_code} 的 {period} 周期数据")
                self._download_and_cache_market_data(clean_code, period, count, cache_file)
                # 重新从缓存加载
                if cache_file.exists():
                    with open(cache_file, 'rb') as f:
                        result[original_code] = pickle.load(f)
                    logger.info(f"下载并缓存成功，股票 {original_code} 的 {period} 周期 {count} 根K线数据")
                else:
                    logger.error(f"下载后仍无法获取股票 {original_code} 的数据")
                    result[original_code] = None
            except Exception as e:
                logger.error(f"下载股票 {original_code} 数据失败: {e}")
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
        trans_code = StockCodeUtils.transform_code_for_xtdata(code)
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
        trans_code_list = [StockCodeUtils.transform_code_for_xtdata(clean_code) for clean_code in clean_code_list]
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


    def get_sector_list(self, all_sectors: Optional[List[str]] = None,
                       start_type: Optional[str] = None,
                       update_data: bool = False) -> Dict[str, Dict]:
        """
        获取板块列表和对应的股票信息

        Args:
            all_sectors: 指定的板块列表，如果为None则获取所有板块
            start_type: 板块前缀过滤条件（如'TGN'表示概念板块）
            update_data: 是否更新板块数据

        Returns:
            包含板块和股票信息的字典:
            {
                'sector_infos': {板块名: [股票代码列表]},
                'stock_infos': {股票代码: [所属板块列表]}
            }
        """
        if self.xtdata is None:
            raise RuntimeError("xtquant未安装，无法获取板块数据")

        sector_infos = {}
        stock_infos = {}

        def update_infos(sector: str, raw_code: str, sector_infos: Dict, stock_infos: Dict):
            """更新板块和股票的映射关系"""
            code = raw_code[:6]  # 提取6位数字代码

            # 更新板块信息
            if sector not in sector_infos:
                sector_infos[sector] = []
            if raw_code not in sector_infos[sector]:
                sector_infos[sector].append(raw_code)

            # 更新股票信息
            if code not in stock_infos:
                stock_infos[code] = []
            if sector not in stock_infos[code]:
                stock_infos[code].append(sector)

        # 更新板块数据
        if update_data:
            logger.info("开始下载板块数据...")
            try:
                self.xtdata.download_sector_data()
                logger.info("板块数据下载完成")
            except Exception as e:
                logger.warning(f"板块数据下载失败: {e}")

        # 获取板块列表
        if all_sectors is None:
            all_sectors = []
            try:
                sector_list = self.xtdata.get_sector_list()
                if sector_list:
                    for sector in sector_list:
                        if start_type is None or sector.startswith(start_type):
                            all_sectors.append(sector)
                logger.info(f"获取到 {len(all_sectors)} 个板块")
            except Exception as e:
                logger.error(f"获取板块列表失败: {e}")
                return {'sector_infos': sector_infos, 'stock_infos': stock_infos}

        # 处理每个板块
        for sector in all_sectors:
            try:
                stock_list = self.xtdata.get_stock_list_in_sector(sector)
                if stock_list:
                    for raw_code in stock_list:
                        update_infos(sector, raw_code, sector_infos, stock_infos)
                else:
                    logger.warning(f"板块 {sector} 没有股票数据")
            except Exception as e:
                logger.warning(f"处理板块 {sector} 时出错: {e}")
                continue

        logger.info(f"成功处理 {len(sector_infos)} 个板块，{len(stock_infos)} 只股票")
        return {'sector_infos': sector_infos, 'stock_infos': stock_infos}

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
        trans_code_list = [StockCodeUtils.transform_code_for_xtdata(clean_code) for clean_code in clean_code_list]
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

    def _download_and_cache_market_data(self, code: str, period: str, count: int, cache_file: Path):
        """下载行情数据并缓存

        Args:
            code: 股票代码（如 '600000'）
            period: 周期（'1d'/'1m'/'5m'）
            count: K线数量
            cache_file: 缓存文件路径
        """
        try:
            from common.qmt_update_data import my_download
        except ImportError:
            logger.error("无法导入qmt_update_data模块，无法下载数据")
            return

        # 计算下载的时间范围
        end_date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

        if period == '1d':
            # 日线数据，估算需要的天数
            days_needed = count * 2  # 多取一些确保够数
            start_date = end_date - timedelta(days=days_needed)
        else:
            # 分钟线数据，取最近几天
            start_date = end_date - timedelta(days=20)

        # 转换格式
        if period.endswith('m'):
            start_dt_str = start_date.strftime("%Y%m%d%H%M%S")
            end_dt_str = end_date.strftime("%Y%m%d%H%M%S")
        else:
            start_dt_str = start_date.strftime("%Y%m%d")
            end_dt_str = end_date.strftime("%Y%m%d")

        # 下载数据
        xtdata_code = StockCodeUtils.format_stock_codes_for_xtdata([code])[0]
        my_download(
            stock_list=[xtdata_code],
            period=period,
            start_date=start_dt_str,
            end_date=end_dt_str,
            logger=logger
        )

        # 下载完成后重新获取数据
        data = self._fetch_market_data_from_xtdata(code, period, count)
        if data is not None:
            # 保存到缓存
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"下载并缓存成功，股票 {code} 的 {period} 周期数据")

