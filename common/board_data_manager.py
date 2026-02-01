"""
板块数据管理器

专门负责板块数据的获取、保存和管理功能。
将原 BoardGraph 中的数据获取和缓存逻辑分离出来。
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

from .board_graph import BoardNodeType
from .utils import StockCodeUtils
from .logger import get_logger

logger = get_logger()


class BoardDataManager:
    """板块数据管理器"""

    # 缓存目录 - 与 date_info 目录保持一致
    CACHE_DIR = Path("/tmp/cache_output/quantara/date_info")
    BOARD_INFO_CACHE = CACHE_DIR / "board_info.pkl"

    def __init__(self):
        """初始化数据管理器"""
        # 确保缓存目录存在
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _collect_industry_info(self) -> Dict[str, Dict]:
        """收集申万行业板块数据"""
        industry_info = {}

        try:
            # 获取申万一级行业
            sw_first = ak.sw_index_first_info()
            for _, row in tqdm(sw_first.iterrows(), desc="处理申万一级行业"):
                code = str(row['行业代码'])
                name = str(row['行业名称'])

                industry_info[code] = {
                    'name': name,
                    'type': BoardNodeType.INDUSTRY_L1.value,
                    'info': row.to_dict(),
                    'cons': self._get_sw_industry_stocks(code),
                    'parent_name': None
                }
                time.sleep(0.1)  # 避免请求过于频繁

        except Exception as e:
            logger.error(f"获取申万一级行业失败: {e}")

        try:
            # 获取申万二级行业
            sw_second = ak.sw_index_second_info()
            for _, row in tqdm(sw_second.iterrows(), desc="处理申万二级行业"):
                code = str(row['行业代码'])
                name = str(row['行业名称'])
                parent_name = str(row['上级行业'])

                industry_info[code] = {
                    'name': name,
                    'type': BoardNodeType.INDUSTRY_L2.value,
                    'info': row.to_dict(),
                    'cons': self._get_sw_industry_stocks(code),
                    'parent_name': parent_name
                }
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"获取申万二级行业失败: {e}")

        try:
            # 获取申万三级行业
            sw_third = ak.sw_index_third_info()
            for _, row in tqdm(sw_third.iterrows(), desc="处理申万三级行业"):
                code = str(row['行业代码'])
                name = str(row['行业名称'])
                parent_name = str(row['上级行业'])

                industry_info[code] = {
                    'name': name,
                    'type': BoardNodeType.INDUSTRY_L3.value,
                    'info': row.to_dict(),
                    'cons': self._get_sw_industry_stocks(code),
                    'parent_name': parent_name
                }
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"获取申万三级行业失败: {e}")

        return industry_info

    def _get_sw_industry_stocks(self, industry_code: str) -> pd.DataFrame:
        """获取申万行业板块内的股票"""
        try:
            df = ak.sw_index_third_cons(symbol=industry_code)
            if not df.empty:
                # 标准化列名
                df = df.rename(columns={
                    'stock_code': '股票代码',
                    'stock_name': '股票简称'
                })
                # 标准化股票代码
                df['股票代码'] = df['股票代码'].astype(str).apply(StockCodeUtils.extract_clean_code)
            return df
        except Exception as e:
            logger.error(f"获取行业 {industry_code} 股票失败: {e}")
            return pd.DataFrame()

    def _collect_concept_info(self) -> Dict[str, Dict]:
        """收集概念板块数据（参考collect_concept_info_from_xtdata）"""
        concept_info = {}

        try:
            # 首先尝试使用DataGetter获取概念板块（更全面的方法）
            from .data_getter import DataGetter
            data_getter = DataGetter()

            # 获取TGN开头的概念板块
            sector_list = data_getter.get_sector_list(all_sectors=None, start_type="TGN", update_data=False)
            logger.info(f"通过DataGetter获取到 {len(sector_list['sector_infos'])} 个概念板块")

            # 处理每个概念板块
            for sec, raw_cons in tqdm(sector_list['sector_infos'].items(), desc="处理概念板块"):
                if not sec.startswith("TGN"):
                    continue

                b_code, b_name, b_type = sec, sec, BoardNodeType.CONCEPT.value
                b_tags = []  # 这里可以扩展为加载标签文件

                cons = {}
                # 处理股票代码映射
                for code_wm in raw_cons:
                    code = StockCodeUtils.extract_clean_code(code_wm)  # 提取干净的股票代码

                    # 尝试获取股票详细信息（这里简化处理）
                    try:
                        # 这里可以扩展为加载stock_base_infos来获取更详细信息
                        cons[code] = {'code': code, 'name': f'Stock_{code}'}
                    except:
                        # 如果无法获取详细信息，至少保留基本信息
                        cons[code] = {'code': code, 'name': f'Stock_{code}'}

                concept_info[sec] = {
                    'code': b_code,
                    'name': b_name,
                    'type': b_type,
                    'cons': cons,
                    'tags': b_tags
                }

        except Exception as e:
            logger.error(f"使用DataGetter获取概念数据失败: {e}")

        logger.info(f"共收集到 {len(concept_info)} 个概念板块")
        return concept_info

    def _collect_index_info(self) -> Dict[str, Dict]:
        """收集指数板块数据（参考collect_index_info_from_xtdata）"""
        index_info = {}

        # 首先尝试使用DataGetter获取更全面的指数列表
        try:
            from .data_getter import DataGetter
            data_getter = DataGetter()

            # 获取更全面的指数列表
            extended_index_list = [
                "上证50", "上证100",
                "沪深300",
                "中证500", "中证1000", "中证2000", "中证A500", "中证TMT", "中证红利",
                "深证1000", "深证红利",
                "创业200", "创业板50", "创业扳指",
                "科创50", "科创100",
                '180R价值', '180R成长', '180价值', '180低贝', '180分层', '180动态', '180基建', '180基本', '180成长', '180治理', '180波动', '180稳定', '180红利', '180资源', '180运输', '180金融', '180高贝',
                '300R价值', '300R成长', '300价值', '300低贝', '300信息', '300公用', '300分层', '300动态', '300医药', '300可选', '300周期', '300地产', '300基建',
                '300工业', '300成长', '300材料', '300波动', '300消费', '300稳定', '300红利', '300绩效', '300能源', '300运输', '300通信', '300金融', '300银行', '300非周', '300高贝',
                '1000价值', '1000信息', '1000公用', '1000医药', '1000可选','1000地产','1000工业', '1000成长', '1000材料', '1000消费', '1000能源', '1000金融'
            ]

            sector_list = data_getter.get_sector_list(all_sectors=extended_index_list, update_data=False)
            logger.info(f"通过DataGetter获取到 {len(sector_list['sector_infos'])} 个指数板块")

            # 处理每个指数板块
            for sec, raw_cons in tqdm(sector_list['sector_infos'].items(), desc="处理指数板块"):
                b_code, b_name, b_type = sec, sec, BoardNodeType.INDEX.value
                cons = {}

                # 处理股票代码映射
                for code_wm in raw_cons:
                    code = StockCodeUtils.extract_clean_code(code_wm)  # 提取6位数字代码

                    # 尝试获取股票基本信息（这里简化处理）
                    try:
                        # 这里可以扩展为加载stock_base_infos来获取更详细信息
                        cons[code] = {'code': code, 'name': f'Stock_{code}'}
                    except:
                        # 如果无法获取详细信息，至少保留基本信息
                        cons[code] = {'code': code, 'name': f'Stock_{code}'}

                index_info[sec] = {
                    'code': b_code,
                    'name': b_name,
                    'type': b_type,
                    'cons': cons,
                    'tags': []
                }

        except Exception as e:
            logger.error(f"使用DataGetter获取指数数据失败: {e}")

        logger.info(f"共收集到 {len(index_info)} 个指数板块")
        return index_info

    def fetch_and_save_board_data(self) -> None:
        """
        获取板块数据并保存到缓存

        直接收集所有板块数据并保存，不依赖其他类实例
        """
        logger.info("开始获取板块数据...")

        try:
            # 从网络获取数据
            industry_info = self._collect_industry_info()
            concept_info = self._collect_concept_info()
            index_info = self._collect_index_info()

            # 创建数据字典
            board_data = {
                'industry_info': industry_info,
                'concept_info': concept_info,
                'index_info': index_info
            }

            # 保存到缓存
            self._save_board_cache(board_data)

            logger.info("板块数据获取并保存完成")

        except Exception as e:
            logger.error(f"获取和保存板块数据失败: {e}")
            raise

    def _save_board_cache(self, board_data: Dict[str, Any]) -> None:
        """
        保存板块数据到缓存文件

        Args:
            board_data: 包含板块数据的字典
        """
        try:
            # 获取当前时间作为更新日期
            update_datetime = datetime.datetime.now()

            board_info = {
                'industry_info': board_data.get('industry_info', {}),
                'concept_info': board_data.get('concept_info', {}),
                'index_info': board_data.get('index_info', {}),
                'update_date': update_datetime.date().isoformat(),  # 更新日期
                'update_datetime': update_datetime.isoformat(),    # 更新日期时间
                'timestamp': update_datetime.timestamp(),           # 时间戳
                'version': '1.0'  # 数据版本
            }

            # 保存到缓存文件
            with open(self.BOARD_INFO_CACHE, 'wb') as f:
                pickle.dump(board_info, f)

            logger.info(f"板块数据已保存到缓存: {self.BOARD_INFO_CACHE}")
            logger.info(f"更新日期: {board_info['update_date']}")
            logger.info(f"数据版本: {board_info['version']}")

        except Exception as e:
            logger.error(f"保存板块数据缓存失败: {e}")
            raise

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存文件的信息

        Returns:
            缓存文件信息字典
        """
        if not self.BOARD_INFO_CACHE.exists():
            raise FileNotFoundError(f"缓存文件不存在: {self.BOARD_INFO_CACHE}")

        try:
            with open(self.BOARD_INFO_CACHE, 'rb') as f:
                board_info = pickle.load(f)

            # 获取文件信息
            stat = self.BOARD_INFO_CACHE.stat()

            return {
                'cache_file': str(self.BOARD_INFO_CACHE),
                'file_size': stat.st_size,
                'modified_time': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'update_date': board_info.get('update_date', 'unknown'),
                'update_datetime': board_info.get('update_datetime', 'unknown'),
                'version': board_info.get('version', 'unknown'),
                'industry_count': len(board_info.get('industry_info', {})),
                'concept_count': len(board_info.get('concept_info', {})),
                'index_count': len(board_info.get('index_info', {}))
            }

        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            raise

    def clear_cache(self) -> None:
        """清除缓存文件"""
        if self.BOARD_INFO_CACHE.exists():
            try:
                self.BOARD_INFO_CACHE.unlink()
                logger.info(f"缓存文件已删除: {self.BOARD_INFO_CACHE}")
            except Exception as e:
                logger.error(f"删除缓存文件失败: {e}")
                raise
        else:
            logger.warning(f"缓存文件不存在: {self.BOARD_INFO_CACHE}")

    @classmethod
    def update_board_data(cls) -> None:
        """
        类方法：更新板块数据

        这是一个便捷方法，用于命令行或脚本调用
        """
        manager = cls()
        manager.fetch_and_save_board_data()

        # 打印缓存信息
        try:
            info = manager.get_cache_info()
            print("✅ 板块数据更新完成")
            print(f"📁 缓存文件: {info['cache_file']}")
            print(f"📅 更新日期: {info['update_date']}")
            print(f"📊 行业板块: {info['industry_count']} 个")
            print(f"📊 概念板块: {info['concept_count']} 个")
            print(f"📊 指数板块: {info['index_count']} 个")
        except Exception as e:
            print(f"⚠️ 获取缓存信息失败: {e}")


def main():
    """主函数，用于命令行调用"""
    import argparse

    parser = argparse.ArgumentParser(description='板块数据管理器')
    parser.add_argument('action', choices=['update', 'info', 'clear'],
                       help='执行操作: update(更新数据), info(查看信息), clear(清除缓存)')

    args = parser.parse_args()

    manager = BoardDataManager()

    try:
        if args.action == 'update':
            print("🔄 开始更新板块数据...")
            manager.update_board_data()

        elif args.action == 'info':
            print("📋 缓存文件信息:")
            info = manager.get_cache_info()
            for key, value in info.items():
                print(f"  {key}: {value}")

        elif args.action == 'clear':
            print("🗑️ 清除缓存文件...")
            manager.clear_cache()
            print("✅ 缓存文件已清除")

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())