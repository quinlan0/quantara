# 金融数据分析智能体 - 详细参考

## MiniQMT xtdata 使用指南

### 初始化连接
```python
from xtquant import xtdata, xtconstant

# 连接到MiniQMT
xtdata.connect(ip="localhost", port=8888)

# 设置数据级别
xtdata.set_token("your_token_here")
```

### 常用数据获取函数

#### 实时行情数据
```python
# 获取实时报价
quote_data = xtdata.get_full_tick(['000001.SZ', '600000.SH'])

# 获取5档报价
level2_data = xtdata.get_l2_quote(['000001.SZ'])

# 订阅实时数据
xtdata.subscribe_quote(['000001.SZ'], callback=quote_callback)
```

#### 历史K线数据
```python
# 获取日K线数据
kline_data = xtdata.get_market_data_ex(
    stock_list=['000001.SZ'],
    period='1d',  # 1d, 1w, 1M等
    start_time='20230101',
    end_time='20231231',
    dividend_type='front'  # 前复权
)

# 获取分钟线数据
minute_data = xtdata.get_market_data_ex(
    stock_list=['000001.SZ'],
    period='1m',  # 1m, 5m, 15m, 30m, 1h等
    start_time='20231201090000',
    end_time='20231201150000'
)
```

## AKShare 数据源详解

### 股票数据
```python
import akshare as ak

# A股股票列表
stock_list = ak.stock_info_a_code_name()

# 沪深股通持股明细
hk_hold = ak.stock_hsgt_hold_stock_em(market="沪股通")

# 个股权重数据
stock_weight = ak.stock_individual_info_em(symbol="000001")
```

### 指数数据
```python
# 上证指数成分股
sz_index_stocks = ak.index_stock_cons_csindex(symbol="000001")

# 指数历史数据
index_history = ak.stock_zh_index_daily_em(
    symbol="sh000001",
    start_date="20230101",
    end_date="20231231"
)
```

### 板块数据
```python
# 行业板块
industry_boards = ak.stock_board_industry_name_em()

# 概念板块
concept_boards = ak.stock_board_concept_name_em()

# 板块成分股
industry_stocks = ak.stock_board_industry_cons_em(symbol="小金属")
```

### 宏观经济数据
```python
# GDP数据
gdp_data = ak.macro_china_gdp()

# CPI数据
cpi_data = ak.macro_china_cpi()

# PMI数据
pmi_data = ak.macro_china_pmi()
```

## 缓存系统实现

### 文件缓存实现
```python
import os
import pickle
import hashlib
from datetime import datetime, timedelta

class FileCache:
    def __init__(self, cache_dir='/tmp/cache_output/quantara'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, func_name, args, kwargs):
        key_data = f"{func_name}_{args}_{kwargs}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key, max_age_hours=24):
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        if not os.path.exists(cache_file):
            return None

        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age > timedelta(hours=max_age_hours):
            os.remove(cache_file)
            return None

        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except:
            return None

    def set(self, key, data):
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
```

### 装饰器缓存
```python
def cached(max_age_hours=24):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = FileCache()
            key = cache._get_cache_key(func.__name__, args, kwargs)

            # 尝试从缓存获取
            cached_data = cache.get(key, max_age_hours)
            if cached_data is not None:
                return cached_data

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator

# 使用示例
@cached(max_age_hours=1)  # 1小时缓存
def get_stock_daily_data(symbol, start_date, end_date):
    # 数据获取逻辑
    return data
```

## 图论分析应用

### 股票关系网络构建
```python
import networkx as nx
import pandas as pd

class StockNetworkAnalyzer:
    def __init__(self):
        self.G = nx.Graph()

    def add_stock_nodes(self, stocks_df):
        for _, stock in stocks_df.iterrows():
            self.G.add_node(
                stock['code'],
                type='stock',
                name=stock['name'],
                industry=stock['industry'],
                concept=stock.get('concept', [])
            )

    def add_sector_nodes(self, sectors_df):
        for _, sector in sectors_df.iterrows():
            self.G.add_node(
                sector['name'],
                type='sector',
                category=sector['category']
            )

    def build_relationships(self, stock_sector_mapping):
        for _, mapping in stock_sector_mapping.iterrows():
            stock_code = mapping['stock_code']
            sector_name = mapping['sector_name']

            if stock_code in self.G and sector_name in self.G:
                self.G.add_edge(stock_code, sector_name, relation='belongs_to')

    def find_related_stocks(self, stock_code, max_distance=2):
        if stock_code not in self.G:
            return []

        # 通过共同板块找到相关股票
        related_stocks = set()
        sectors = [n for n in self.G.neighbors(stock_code)
                  if self.G.nodes[n]['type'] == 'sector']

        for sector in sectors:
            sector_stocks = [n for n in self.G.neighbors(sector)
                           if n != stock_code and self.G.nodes[n]['type'] == 'stock']
            related_stocks.update(sector_stocks)

        return list(related_stocks)

    def analyze_sector_influence(self, sector_name):
        if sector_name not in self.G:
            return {}

        # 计算板块影响力
        stocks_in_sector = [n for n in self.G.neighbors(sector_name)
                          if self.G.nodes[n]['type'] == 'stock']

        # 计算板块间关联
        related_sectors = set()
        for stock in stocks_in_sector:
            stock_sectors = [n for n in self.G.neighbors(stock)
                           if n != sector_name and self.G.nodes[n]['type'] == 'sector']
            related_sectors.update(stock_sectors)

        return {
            'stock_count': len(stocks_in_sector),
            'related_sectors': list(related_sectors),
            'influence_score': len(stocks_in_sector) * len(related_sectors)
        }
```

### 网络分析指标
```python
def calculate_network_metrics(G):
    metrics = {}

    # 度中心性
    degree_centrality = nx.degree_centrality(G)
    metrics['degree_centrality'] = degree_centrality

    # 介数中心性
    betweenness_centrality = nx.betweenness_centrality(G)
    metrics['betweenness_centrality'] = betweenness_centrality

    # 紧密中心性
    closeness_centrality = nx.closeness_centrality(G)
    metrics['closeness_centrality'] = closeness_centrality

    # 聚类系数
    clustering = nx.clustering(G)
    metrics['clustering'] = clustering

    return metrics
```

## 数据验证和清洗

### 数据质量检查
```python
import pandas as pd
import numpy as np

class DataValidator:
    @staticmethod
    def validate_kline_data(df):
        """验证K线数据完整性"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']

        # 检查必需列
        if not all(col in df.columns for col in required_cols):
            return False, "缺少必需列"

        # 检查数据类型
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                return False, f"{col}列不是数值类型"

        # 检查数据合理性
        if (df['high'] < df['low']).any():
            return False, "存在最高价低于最低价的数据"

        if (df['close'] < 0).any():
            return False, "存在负的收盘价"

        return True, "数据验证通过"

    @staticmethod
    def clean_price_data(df):
        """清理价格数据"""
        # 移除异常值
        df = df[df['close'] > 0]  # 移除负价格
        df = df[df['volume'] >= 0]  # 移除负成交量

        # 处理缺失值
        df = df.fillna(method='ffill')  # 前向填充

        # 移除重复数据
        df = df.drop_duplicates(subset=['date'])

        return df
```

## 性能优化技巧

### 内存优化
```python
def memory_efficient_dataframe_processing(df, chunk_size=10000):
    """分块处理大数据框"""
    results = []

    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        # 处理当前块
        processed_chunk = process_chunk(chunk)
        results.append(processed_chunk)

        # 强制垃圾回收
        if i % (chunk_size * 10) == 0:
            import gc
            gc.collect()

    return pd.concat(results, ignore_index=True)

def optimize_dataframe_dtypes(df):
    """优化DataFrame数据类型以节省内存"""
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = pd.to_numeric(df[col], downcast='float')
        elif df[col].dtype == 'int64':
            df[col] = pd.to_numeric(df[col], downcast='integer')

    return df
```

### 并行处理
```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

async def fetch_multiple_stocks_async(symbols, fetch_func):
    """异步获取多个股票数据"""
    async def fetch_single(symbol):
        return await asyncio.get_event_loop().run_in_executor(
            None, fetch_func, symbol
        )

    tasks = [fetch_single(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return dict(zip(symbols, results))

def parallel_data_processing(data_list, process_func, max_workers=4):
    """并行数据处理"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_func, data_list))
    return results
```

## 错误处理和重试机制

### 网络请求重试
```python
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError))
)
def robust_api_call(url, params=None):
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()
```

### 数据源故障转移
```python
class DataSourceManager:
    def __init__(self):
        self.sources = {
            'primary': PrimaryDataSource(),
            'backup': BackupDataSource(),
            'fallback': FallbackDataSource()
        }

    def get_data(self, symbol, **kwargs):
        for source_name, source in self.sources.items():
            try:
                data = source.fetch_data(symbol, **kwargs)
                if self.validate_data(data):
                    return data
            except Exception as e:
                print(f"{source_name}数据源失败: {e}")
                continue

        raise Exception("所有数据源都无法获取数据")
```

## 监控和日志

### 性能监控
```python
import time
import logging
from functools import wraps

def performance_monitor(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = get_memory_usage()

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            end_memory = get_memory_usage()

            logging.info(
                f"{func.__name__} 执行时间: {end_time - start_time:.2f}s, "
                f"内存变化: {end_memory - start_memory:.2f}MB"
            )

            return result
        except Exception as e:
            logging.error(f"{func.__name__} 执行失败: {e}")
            raise

    return wrapper

# 使用示例
@performance_monitor
def get_large_dataset():
    # 耗时操作
    pass
```

### 数据质量监控
```python
class DataQualityMonitor:
    def __init__(self):
        self.metrics = {}

    def track_data_quality(self, data_source, data):
        if data_source not in self.metrics:
            self.metrics[data_source] = {
                'total_requests': 0,
                'successful_requests': 0,
                'data_quality_score': 0,
                'last_updated': None
            }

        self.metrics[data_source]['total_requests'] += 1

        # 计算数据质量分数
        quality_score = self.calculate_quality_score(data)
        self.metrics[data_source]['data_quality_score'] = quality_score
        self.metrics[data_source]['last_updated'] = datetime.now()

        if quality_score > 0.8:  # 质量阈值
            self.metrics[data_source]['successful_requests'] += 1

    def calculate_quality_score(self, data):
        """计算数据质量分数"""
        score = 1.0

        if isinstance(data, pd.DataFrame):
            # 检查数据完整性
            null_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
            score -= null_ratio * 0.3

            # 检查数据合理性
            if 'close' in data.columns:
                negative_prices = (data['close'] < 0).sum()
                score -= (negative_prices / len(data)) * 0.5

        return max(0, score)
```