"""
通用工具函数模块

提供项目中常用的工具函数，包括股票代码转换、数据处理等功能。
"""

import re
from typing import List, Dict, Any, Optional


class StockCodeUtils:
    """股票代码处理工具类"""

    @staticmethod
    def transform_code(code: str) -> str:
        """转换股票代码格式为6位数字格式

        支持的输入格式：
        - '000001.SH' -> '000001' (点号后缀格式)
        - 'SH000001' -> '000001' (前缀格式)
        - '000001SH' -> '000001' (后缀格式，无点号)
        - '000001sh' -> '000001' (小写后缀格式)
        - 'sh000001' -> '000001' (小写前缀格式)
        - '000001' -> '000001' (已有6位数字格式)

        Args:
            code: 输入的股票代码

        Returns:
            6位数字格式的股票代码

        Raises:
            ValueError: 当代码格式不支持时
        """
        if not code:
            raise ValueError("股票代码不能为空")

        code = str(code).strip().upper()

        # 移除交易所后缀
        code = re.sub(r'\.(SH|SZ|BJ)$', '', code)

        # 处理前缀格式 (SH000001, SZ600000, BJ000001)
        if code.startswith(('SH', 'SZ', 'BJ')):
            # SH000001 -> 000001
            if len(code) == 8 and code[2:].isdigit():
                return code[2:]
            else:
                raise ValueError(f"不支持的代码格式: {code}")
        else:
            # 处理后缀格式 (000001.SH, 600000.SZ, 000001.BJ)
            suffix_match = re.search(r'^(\d{6})(SH|SZ|BJ)$', code)
            if suffix_match:
                return suffix_match.group(1)

            # 已经是6位数字格式
            if len(code) == 6 and code.isdigit():
                return code
            else:
                raise ValueError(f"不支持的代码格式: {code}")

    @staticmethod
    def transform_code_for_xtdata(code: str) -> str:
        """转换股票代码格式为xtdata所需格式

        Args:
            code: 6位数字格式的股票代码

        Returns:
            xtdata所需的格式，如'000001.SZ'

        Raises:
            ValueError: 当无法确定交易所或代码格式错误时
        """
        # 首先转换为6位数字格式
        clean_code = StockCodeUtils.transform_code(code)

        # 根据规则添加交易所后缀
        if clean_code.startswith(('6', '5')):
            return f"{clean_code}.SH"
        elif clean_code.startswith(('0', '3', '1')):
            return f"{clean_code}.SZ"
        elif clean_code.startswith(('8', '9', '4')):
            return f"{clean_code}.BJ"
        else:
            raise ValueError(f"无法确定交易所: {clean_code}")

    @staticmethod
    def normalize_stock_codes(codes: List[str]) -> List[str]:
        """批量标准化股票代码为6位数字格式

        Args:
            codes: 股票代码列表

        Returns:
            标准化后的6位数字代码列表
        """
        return [StockCodeUtils.transform_code(code) for code in codes]

    @staticmethod
    def format_stock_codes_for_xtdata(codes: List[str]) -> List[str]:
        """批量转换股票代码为xtdata格式

        Args:
            codes: 6位数字格式的股票代码列表

        Returns:
            xtdata格式的代码列表
        """
        return [StockCodeUtils.transform_code_for_xtdata(code) for code in codes]

    @staticmethod
    def extract_clean_code(code_str: str, max_length: int = 6) -> str:
        """从字符串中提取干净的股票代码

        Args:
            code_str: 包含股票代码的字符串
            max_length: 代码最大长度，默认6位

        Returns:
            提取的干净代码
        """
        if not code_str:
            return ""

        # 转换为字符串并清理
        code = str(code_str).strip()

        # 提取数字部分
        digits = re.findall(r'\d+', code)
        if digits:
            # 取第一个数字序列的前max_length位
            return digits[0][:max_length]

        return ""

    @staticmethod
    def is_valid_stock_code(code: str) -> bool:
        """验证股票代码是否有效

        Args:
            code: 股票代码

        Returns:
            是否为有效的股票代码
        """
        try:
            clean_code = StockCodeUtils.transform_code(code)
            return len(clean_code) == 6 and clean_code.isdigit()
        except ValueError:
            return False

    @staticmethod
    def get_exchange_suffix(code: str) -> str:
        """根据股票代码获取交易所后缀

        Args:
            code: 6位数字格式的股票代码

        Returns:
            交易所后缀 ('SH', 'SZ', 'BJ')
        """
        clean_code = StockCodeUtils.transform_code(code)

        if clean_code.startswith(('6', '5')):
            return 'SH'
        elif clean_code.startswith(('0', '3', '1')):
            return 'SZ'
        elif clean_code.startswith(('8', '9', '4')):
            return 'BJ'
        else:
            raise ValueError(f"无法确定交易所: {clean_code}")


class DataProcessingUtils:
    """数据处理工具类"""

    @staticmethod
    def safe_strip(value: Any) -> str:
        """安全地转换为字符串并去除空白字符

        Args:
            value: 输入值

        Returns:
            处理后的字符串
        """
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """安全地转换为整数

        Args:
            value: 输入值
            default: 默认值

        Returns:
            转换后的整数
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """安全地转换为浮点数

        Args:
            value: 输入值
            default: 默认值

        Returns:
            转换后的浮点数
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def merge_dicts(*dicts: Dict) -> Dict:
        """合并多个字典，后面的字典会覆盖前面的

        Args:
            *dicts: 要合并的字典

        Returns:
            合并后的字典
        """
        result = {}
        for d in dicts:
            if d:
                result.update(d)
        return result


# 为了向后兼容，提供模块级别的函数
def transform_code(code: str) -> str:
    """转换股票代码格式为6位数字格式（向后兼容）"""
    return StockCodeUtils.transform_code(code)


def transform_code_for_xtdata(code: str) -> str:
    """转换股票代码格式为xtdata所需格式（向后兼容）"""
    return StockCodeUtils.transform_code_for_xtdata(code)


def normalize_stock_codes(codes: List[str]) -> List[str]:
    """批量标准化股票代码为6位数字格式（向后兼容）"""
    return StockCodeUtils.normalize_stock_codes(codes)


def format_stock_codes_for_xtdata(codes: List[str]) -> List[str]:
    """批量转换股票代码为xtdata格式（向后兼容）"""
    return StockCodeUtils.format_stock_codes_for_xtdata(codes)