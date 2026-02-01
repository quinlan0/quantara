"""
股票基本信息管理器

专门负责股票基本信息的获取、保存和管理功能。
类似于 BoardDataManager，但专注于股票基本信息。
"""

import os
import pickle
import datetime
import time
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import akshare as ak
from tqdm import tqdm

# 导入xtdata
try:
    from xtquant import xtdata
    xtdata.enable_hello = False
    XTDATA_AVAILABLE = True
except ImportError:
    XTDATA_AVAILABLE = False
    logger.warning("xtquant不可用，将使用akshare作为备选方案")

from .utils import StockCodeUtils
from .logger import get_logger

logger = get_logger()


class StockBasicInfoManager:
    """股票基本信息管理器"""

    # 缓存目录 - 与 date_info 目录保持一致
    CACHE_DIR = Path("/tmp/cache_output/quantara/date_info")
    STOCK_BASIC_INFO_CACHE = CACHE_DIR / "stock_basic_info.pkl"
    STOCK_CODES_CACHE = CACHE_DIR / "stock_codes.pkl"

    def __init__(self, xtdata_client=None):
        """初始化管理器

        Args:
            xtdata_client: xtdata客户端实例，用于获取更详细的股票信息
        """
        self.xtdata = xtdata_client if xtdata_client else (xtdata if XTDATA_AVAILABLE else None)
        # 确保缓存目录存在
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_and_save_stock_basic_info(self) -> None:
        """
        获取所有股票基本信息并保存到缓存

        通过 akshare 获取全部A股股票代码，然后获取详细信息并保存。
        """
        logger.info("开始获取所有股票基本信息...")

        try:
            # 获取所有A股股票代码
            all_codes = self._get_all_stock_codes()

            # 获取股票详细信息
            stock_data = self._collect_stock_basic_info(all_codes)

            # 保存到缓存
            self._save_stock_basic_cache(stock_data)

            logger.info("股票基本信息获取并保存完成")

        except Exception as e:
            logger.error(f"获取和保存股票基本信息失败: {e}")
            raise

    def _get_all_stock_codes(self) -> list:
        """
        获取所有A股股票代码（带缓存机制）

        Returns:
            股票代码列表
        """
        import datetime

        # 检查缓存
        if self.STOCK_CODES_CACHE.exists():
            try:
                with open(self.STOCK_CODES_CACHE, 'rb') as f:
                    cache_data = pickle.load(f)

                # 检查缓存是否过期（24小时）
                cache_time = cache_data.get('timestamp', 0)
                current_time = datetime.datetime.now().timestamp()

                if current_time - cache_time < 24 * 3600:  # 24小时
                    codes = cache_data.get('codes', [])
                    logger.info(f"从缓存加载股票代码: {len(codes)} 只")
                    return codes
                else:
                    logger.info("股票代码缓存已过期，重新获取")

            except Exception as e:
                logger.warning(f"读取股票代码缓存失败: {e}")

        # 从网络获取股票代码
        logger.info("从网络获取所有A股股票代码...")

        try:
            # 使用akshare获取A股股票代码和名称数据
            raw_data = ak.stock_info_a_code_name()
            codes = raw_data['code'].astype(str).tolist()

            # 转换为6位数字格式并去重
            clean_codes = list(set(StockCodeUtils.normalize_stock_codes(codes)))

            # 保存到缓存
            cache_data = {
                'codes': clean_codes,
                'timestamp': datetime.datetime.now().timestamp(),
                'update_date': datetime.datetime.now().date().isoformat(),
                'total_count': len(clean_codes)
            }

            with open(self.STOCK_CODES_CACHE, 'wb') as f:
                pickle.dump(cache_data, f)

            logger.info(f"获取到 {len(clean_codes)} 只A股股票代码并已缓存")
            return clean_codes

        except Exception as e:
            logger.error(f"获取A股股票代码失败: {e}")
            raise

    def _collect_stock_basic_info(self, codes: list) -> list:
        """
        收集股票基本信息（参考new_data_getter.py的get_base_infos方法）

        Args:
            codes: 股票代码列表（6位数字格式）

        Returns:
            股票基本信息列表
        """
        logger.info(f"开始收集 {len(codes)} 只股票的基本信息")

        stock_data = []

        # 转换为xtdata格式的代码列表
        xtdata_codes = StockCodeUtils.format_stock_codes_for_xtdata(codes)

        for xtdata_code in tqdm(xtdata_codes, desc="获取股票详细信息"):
            try:
                # 使用xtdata获取股票详细信息
                detail = self.xtdata.get_instrument_detail(xtdata_code)
                if detail is None:
                    logger.warning(f"无法获取股票 {xtdata_code} 的详细信息")
                    continue

                # 构建股票信息（参考new_data_getter.py的逻辑）
                stock_info = {
                    'code': detail['InstrumentID'],  # 6位数字代码
                    'name': detail['InstrumentName'],  # 股票名称
                    'total_shares': detail.get('TotalVolume'),  # 总股本
                    'cir_shares': detail.get('FloatVolume'),    # 流通股本
                    'price': detail.get('PreClose'),           # 最新价格
                }

                # 计算市值（参考new_data_getter.py的计算方式）
                if stock_info['price'] and stock_info['total_shares']:
                    stock_info['total_mv'] = stock_info['total_shares'] * stock_info['price']
                else:
                    stock_info['total_mv'] = None

                if stock_info['price'] and stock_info['cir_shares']:
                    stock_info['cir_mv'] = stock_info['cir_shares'] * stock_info['price']
                else:
                    stock_info['cir_mv'] = None

                # PE和PB暂时设为None，后续可以通过财务数据计算
                stock_info['pe'] = None
                stock_info['pb'] = None

                stock_data.append(stock_info)

            except Exception as e:
                logger.warning(f"获取股票 {xtdata_code} 信息失败: {e}")
                continue

        # 如果xtdata获取失败，回退到akshare
        if not stock_data and not XTDATA_AVAILABLE:
            logger.warning("xtdata不可用，回退到akshare获取基本信息")
            stock_data = self._fallback_to_akshare(codes)

        logger.info(f"成功收集 {len(stock_data)} 只股票的基本信息")
        return stock_data

    def _fallback_to_akshare(self, codes: list) -> list:
        """
        回退方法：使用akshare获取基本信息

        Args:
            codes: 股票代码列表

        Returns:
            股票基本信息列表
        """
        stock_data = []

        try:
            # 获取A股实时行情数据
            raw_data = ak.stock_zh_a_spot_em()

            # 过滤指定代码的股票
            mask = raw_data['代码'].astype(str).isin(codes)
            filtered_data = raw_data[mask]

            # 转换数据格式
            for _, row in filtered_data.iterrows():
                stock_info = {
                    'code': str(row['代码']),
                    'name': str(row['名称']),
                    'total_mv': float(row['总市值']) if pd.notna(row['总市值']) else None,
                    'cir_mv': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                    'pe': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                    'pb': float(row['市净率']) if pd.notna(row['市净率']) else None,
                    'total_shares': None,  # akshare不直接提供股本信息
                    'cir_shares': None
                }
                stock_data.append(stock_info)

        except Exception as e:
            logger.error(f"akshare回退获取失败: {e}")

        return stock_data



    def _save_stock_basic_cache(self, stock_data: list) -> None:
        """
        保存股票基本信息到缓存文件

        Args:
            stock_data: 股票基本信息列表
        """
        try:
            # 获取当前时间作为更新日期
            update_datetime = datetime.datetime.now()

            stock_info = {
                'stock_data': stock_data,
                'update_date': update_datetime.date().isoformat(),  # 更新日期
                'update_datetime': update_datetime.isoformat(),    # 更新日期时间
                'timestamp': update_datetime.timestamp(),           # 时间戳
                'version': '1.0',                                   # 数据版本
                'total_count': len(stock_data)                      # 总股票数量
            }

            # 保存到缓存文件
            with open(self.STOCK_BASIC_INFO_CACHE, 'wb') as f:
                pickle.dump(stock_info, f)

            logger.info(f"股票基本信息已保存到缓存: {self.STOCK_BASIC_INFO_CACHE}")
            logger.info(f"更新日期: {stock_info['update_date']}")
            logger.info(f"数据版本: {stock_info['version']}")
            logger.info(f"股票数量: {stock_info['total_count']}")

        except Exception as e:
            logger.error(f"保存股票基本信息缓存失败: {e}")
            raise

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取股票基本信息缓存文件的信息

        Returns:
            缓存文件信息字典
        """
        if not self.STOCK_BASIC_INFO_CACHE.exists():
            raise FileNotFoundError(f"缓存文件不存在: {self.STOCK_BASIC_INFO_CACHE}")

        try:
            with open(self.STOCK_BASIC_INFO_CACHE, 'rb') as f:
                stock_info = pickle.load(f)

            # 获取文件信息
            stat = self.STOCK_BASIC_INFO_CACHE.stat()

            return {
                'cache_file': str(self.STOCK_BASIC_INFO_CACHE),
                'file_size': stat.st_size,
                'modified_time': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'update_date': stock_info.get('update_date', 'unknown'),
                'update_datetime': stock_info.get('update_datetime', 'unknown'),
                'version': stock_info.get('version', 'unknown'),
                'total_count': stock_info.get('total_count', 0)
            }

        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            raise

    def get_stock_codes_cache_info(self) -> Dict[str, Any]:
        """
        获取股票代码缓存文件的信息

        Returns:
            股票代码缓存文件信息字典
        """
        if not self.STOCK_CODES_CACHE.exists():
            raise FileNotFoundError(f"股票代码缓存文件不存在: {self.STOCK_CODES_CACHE}")

        try:
            with open(self.STOCK_CODES_CACHE, 'rb') as f:
                cache_data = pickle.load(f)

            # 获取文件信息
            stat = self.STOCK_CODES_CACHE.stat()

            return {
                'cache_file': str(self.STOCK_CODES_CACHE),
                'file_size': stat.st_size,
                'modified_time': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'update_date': cache_data.get('update_date', 'unknown'),
                'total_count': cache_data.get('total_count', 0),
                'is_expired': datetime.datetime.now().timestamp() - cache_data.get('timestamp', 0) > 24 * 3600
            }

        except Exception as e:
            logger.error(f"获取股票代码缓存信息失败: {e}")
            raise

    def clear_cache(self) -> None:
        """清除所有缓存文件"""
        caches_to_clear = [
            (self.STOCK_BASIC_INFO_CACHE, "股票基本信息缓存"),
            (self.STOCK_CODES_CACHE, "股票代码缓存")
        ]

        for cache_file, cache_name in caches_to_clear:
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    logger.info(f"{cache_name}文件已删除: {cache_file}")
                except Exception as e:
                    logger.error(f"删除{cache_name}文件失败: {e}")
                    raise
            else:
                logger.warning(f"{cache_name}文件不存在: {cache_file}")

    @classmethod
    def update_stock_basic_info(cls) -> None:
        """
        类方法：更新股票基本信息

        这是一个便捷方法，用于命令行或脚本调用
        """
        manager = cls()
        manager.fetch_and_save_stock_basic_info()

        # 打印缓存信息
        try:
            info = manager.get_cache_info()
            print("✅ 股票基本信息更新完成")
            print(f"📁 缓存文件: {info['cache_file']}")
            print(f"📅 更新日期: {info['update_date']}")
            print(f"📊 股票数量: {info['total_count']}")
        except Exception as e:
            print(f"⚠️ 获取股票基本信息缓存失败: {e}")

        # 同时打印股票代码缓存信息
        try:
            codes_info = manager.get_stock_codes_cache_info()
            print(f"\n📋 股票代码缓存: {codes_info['total_count']} 只股票")
        except Exception as e:
            print(f"⚠️ 获取股票代码缓存信息失败: {e}")


def main():
    """主函数，用于命令行调用"""
    import argparse

    parser = argparse.ArgumentParser(description='股票基本信息管理器')
    parser.add_argument('action', choices=['update', 'info', 'clear'],
                       help='执行操作: update(更新数据), info(查看信息), clear(清除缓存)')

    args = parser.parse_args()

    manager = StockBasicInfoManager()

    try:
        if args.action == 'update':
            print("🔄 开始更新股票基本信息...")
            print("这可能需要几分钟时间，请耐心等待...")
            print()
            manager.update_stock_basic_info()

        elif args.action == 'info':
            print("📋 股票基本信息缓存:")
            try:
                info = manager.get_cache_info()
                for key, value in info.items():
                    print(f"  {key}: {value}")
            except FileNotFoundError as e:
                print(f"  ⚠️ {e}")

            print("\n📋 股票代码缓存:")
            try:
                codes_info = manager.get_stock_codes_cache_info()
                for key, value in codes_info.items():
                    if key == 'is_expired' and value:
                        print(f"  {key}: {value} ⚠️")
                    else:
                        print(f"  {key}: {value}")
            except FileNotFoundError as e:
                print(f"  ⚠️ {e}")

        elif args.action == 'clear':
            print("🗑️ 清除所有缓存文件...")
            manager.clear_cache()
            print("✅ 缓存文件已清除")

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())