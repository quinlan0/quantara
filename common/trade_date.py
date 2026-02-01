"""
交易日期管理模块
提供交易日历查询和管理功能
"""

import pandas as pd
import numpy as np
import akshare as ak
import datetime
from typing import Optional, Union, List


class TradeDate:
    """交易日期管理类"""

    def __init__(self, refresh: bool = False):
        """
        初始化交易日期管理器

        Args:
            refresh: 是否强制刷新交易日历数据
        """
        self._data = None
        self._load_data(refresh)

    def _load_data(self, refresh: bool = False) -> None:
        """
        加载交易日历数据

        Args:
            refresh: 是否强制刷新
        """
        try:
            # 获取交易日历数据
            raw_data = ak.tool_trade_date_hist_sina()

            if raw_data is not None and not raw_data.empty:
                # 确保日期列格式正确
                if 'trade_date' in raw_data.columns:
                    raw_data['trade_date'] = pd.to_datetime(raw_data['trade_date']).dt.date
                    raw_data = raw_data.sort_values('trade_date').reset_index(drop=True)

                self._data = raw_data
            else:
                raise ValueError("获取的交易日历数据为空")

        except Exception as e:
            raise RuntimeError(f"加载交易日历数据失败: {e}")

    def get_date_index(self, date: Union[datetime.datetime, datetime.date, str]) -> Optional[int]:
        """
        获取指定日期在交易日历中的索引

        Args:
            date: 日期对象或字符串

        Returns:
            日期索引，如果不是交易日则返回None
        """
        if self._data is None:
            return None

        # 转换日期格式
        target_date = self._normalize_date(date)
        if target_date is None:
            return None

        # 查找匹配的日期
        mask = self._data['trade_date'] == target_date
        matches = self._data[mask]

        if len(matches) == 0:
            return None

        return matches.index.tolist()[0]

    def _normalize_date(self, date: Union[datetime.datetime, datetime.date, str]) -> Optional[datetime.date]:
        """
        规范化日期格式

        Args:
            date: 输入日期

        Returns:
            标准化的日期对象
        """
        try:
            if isinstance(date, datetime.datetime):
                return date.date()
            elif isinstance(date, datetime.date):
                return date
            elif isinstance(date, str):
                # 支持多种字符串格式
                return pd.to_datetime(date).date()
            else:
                return None
        except (ValueError, TypeError):
            return None

    def is_trade_date(self, date: Union[datetime.datetime, datetime.date, str]) -> bool:
        """
        判断指定日期是否为交易日

        Args:
            date: 待检查的日期

        Returns:
            是否为交易日
        """
        return self.get_date_index(date) is not None

    def get_date(self, index: int) -> Optional[datetime.date]:
        """
        根据索引获取交易日期

        Args:
            index: 日期索引

        Returns:
            交易日期
        """
        if self._data is None or index < 0 or index >= len(self._data):
            return None

        return self._data.iloc[index]['trade_date']

    def get_delta_days(self, start_date: Union[datetime.datetime, datetime.date, str],
                      end_date: Union[datetime.datetime, datetime.date, str]) -> Optional[int]:
        """
        计算两个交易日之间的交易日天数差

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日天数差，None表示日期无效
        """
        start_index = self.get_date_index(start_date)
        end_index = self.get_date_index(end_date)

        if start_index is not None and end_index is not None:
            return end_index - start_index

        return None

    def get_trade_dates_in_range(self, start_date: Union[datetime.datetime, datetime.date, str],
                                end_date: Union[datetime.datetime, datetime.date, str]) -> List[datetime.date]:
        """
        获取指定日期范围内的所有交易日

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日列表
        """
        if self._data is None:
            return []

        start = self._normalize_date(start_date)
        end = self._normalize_date(end_date)

        if start is None or end is None:
            return []

        # 筛选日期范围内的交易日
        mask = (self._data['trade_date'] >= start) & (self._data['trade_date'] <= end)
        trade_dates = self._data[mask]['trade_date'].tolist()

        return sorted(trade_dates)

    def get_previous_trade_date(self, date: Union[datetime.datetime, datetime.date, str]) -> Optional[datetime.date]:
        """
        获取指定日期的前一个交易日

        Args:
            date: 基准日期

        Returns:
            前一个交易日
        """
        index = self.get_date_index(date)
        if index is not None and index > 0:
            return self.get_date(index - 1)
        return None

    def get_next_trade_date(self, date: Union[datetime.datetime, datetime.date, str]) -> Optional[datetime.date]:
        """
        获取指定日期的后一个交易日

        Args:
            date: 基准日期

        Returns:
            后一个交易日
        """
        index = self.get_date_index(date)
        if index is not None and index < len(self._data) - 1:
            return self.get_date(index + 1)
        return None

    def get_latest_trade_date(self) -> Optional[datetime.date]:
        """
        获取最新的交易日

        Returns:
            最新交易日
        """
        if self._data is None or len(self._data) == 0:
            return None

        return self._data.iloc[-1]['trade_date']

    @property
    def data(self) -> Optional[pd.DataFrame]:
        """获取交易日历数据"""
        return self._data.copy() if self._data is not None else None

    def refresh_data(self) -> None:
        """刷新交易日历数据"""
        self._load_data(refresh=True)


if __name__ == "__main__":
    # 测试示例
    trade_date = TradeDate()
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)

    print(f"昨天 {yesterday.date()} 是否为交易日: {trade_date.is_trade_date(yesterday)}")
    print(f"今天 {today.date()} 是否为交易日: {trade_date.is_trade_date(today)}")

    # 测试前一个交易日
    prev_trade_date = trade_date.get_previous_trade_date(today)
    print(f"今天的前一个交易日: {prev_trade_date}")

    # 测试交易日范围
    week_ago = today - datetime.timedelta(days=7)
    recent_trade_dates = trade_date.get_trade_dates_in_range(week_ago, today)
    print(f"最近一周的交易日: {recent_trade_dates}")

    # 测试交易日天数差
    if prev_trade_date:
        delta = trade_date.get_delta_days(prev_trade_date, trade_date.get_latest_trade_date())
        print(f"最新交易日距离前一个交易日的交易日天数: {delta}")