---
name: financial-data-agent
description: 提供股票、期货等金融市场的行情数据、新闻、基本面数据获取和分析，使用miniqmt、akshare等数据源，采用缓存优化性能。适用于量化交易数据分析、金融市场研究、股票板块分析等场景。
---

# 金融数据分析智能体

## 概述

该智能体专注于金融市场数据的获取、处理和分析，特别擅长：
- 股票、期货等金融产品行情数据
- 市场新闻和基本面数据
- 行业板块、概念板块、指数板块分析
- 通过图论思维理解股票和板块间关系

## 核心能力

### 数据源接口

#### MiniQMT xtdata 使用
使用xtdata获取实时和历史行情数据：

```python
from xtquant import xtdata

# 获取股票历史K线数据
data = xtdata.get_market_data_ex(
    stock_list=['000001.SZ'],
    period='1d',
    start_time='20240101',
    end_time='20241231'
)
```

#### AKShare 数据接口
使用akshare获取各类金融数据：

```python
import akshare as ak

# 获取股票基本信息
stock_info = ak.stock_info_a_code_name()

# 获取宏观经济数据
macro_data = ak.macro_china_gdp()

# 获取行业板块数据
industry_data = ak.stock_board_industry_name_em()
```

### 数据格式和返回

始终返回用户期望的数据格式：

```python
# 返回pandas DataFrame
def get_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    # 数据获取逻辑
    return df

# 返回字典格式
def get_market_news() -> dict:
    return {
        'timestamp': datetime.now(),
        'news': news_list,
        'sources': ['source1', 'source2']
    }
```

### 性能优化和缓存

#### 缓存策略
使用本地文件缓存和内存缓存优化性能：

```python
import os
from functools import lru_cache
import pickle

CACHE_DIR = '/tmp/cache_output/quantara'

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

@lru_cache(maxsize=100)
def get_cached_data(key: str):
    cache_file = os.path.join(CACHE_DIR, f'{key}.pkl')
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return None

def save_to_cache(key: str, data):
    ensure_cache_dir()
    cache_file = os.path.join(CACHE_DIR, f'{key}.pkl')
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)
```

#### 数据库缓存
对于大数据量，使用SQLite进行缓存：

```python
import sqlite3
import pandas as pd

def create_cache_table():
    conn = sqlite3.connect(os.path.join(CACHE_DIR, 'cache.db'))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS data_cache (
            key TEXT PRIMARY KEY,
            data BLOB,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def cache_dataframe(key: str, df: pd.DataFrame):
    conn = sqlite3.connect(os.path.join(CACHE_DIR, 'cache.db'))
    df.to_sql(key, conn, if_exists='replace', index=False)
    conn.close()
```

### 板块分析思维

#### 图论思维应用
使用NetworkX分析股票和板块关系：

```python
import networkx as nx

def build_sector_graph(stocks, sectors):
    G = nx.Graph()

    # 添加股票节点
    for stock in stocks:
        G.add_node(stock['code'], type='stock', **stock)

    # 添加板块节点
    for sector in sectors:
        G.add_node(sector['name'], type='sector', **sector)

    # 建立股票-板块关系边
    for stock in stocks:
        for sector_name in stock['sectors']:
            G.add_edge(stock['code'], sector_name, relation='belongs_to')

    return G

# 分析板块影响力
def analyze_sector_influence(G, sector_name):
    # 计算板块内股票的连接强度
    neighbors = list(G.neighbors(sector_name))
    influence_score = len(neighbors)

    # 计算板块间的关联度
    related_sectors = []
    for neighbor in neighbors:
        if G.nodes[neighbor]['type'] == 'stock':
            for sector_neighbor in G.neighbors(neighbor):
                if sector_neighbor != sector_name:
                    related_sectors.append(sector_neighbor)

    return {
        'influence_score': influence_score,
        'related_sectors': list(set(related_sectors))
    }
```

## 使用场景

### 行情数据获取
```
用户: 获取上证指数最近30天的日K线数据
智能体: 使用akshare或xtdata获取数据，返回DataFrame格式
```

### 基本面分析
```
用户: 分析新能源汽车板块的财务指标
智能体: 获取板块内公司财务数据，进行对比分析
```

### 新闻情感分析
```
用户: 获取今天的市场新闻并分析情感
智能体: 调用新闻API，结合NLP进行情感分析
```

### 板块关系图谱
```
用户: 展示人工智能板块和相关概念的关系图
智能体: 构建网络图，展示股票-板块-概念的关联关系
```

## 数据质量保证

### 数据验证
```python
def validate_stock_data(df: pd.DataFrame) -> bool:
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    return all(col in df.columns for col in required_columns)
```

### 异常处理
```python
def safe_data_fetch(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if validate_data(result):
                return result
            else:
                logger.warning("数据验证失败")
                return None
        except Exception as e:
            logger.error(f"数据获取失败: {e}")
            return None
    return wrapper
```

## 性能监控

### 缓存命中率统计
```python
class CacheStats:
    def __init__(self):
        self.hits = 0
        self.misses = 0

    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0
```

### 内存使用监控
```python
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB
```

## 最佳实践

1. **优先使用缓存**: 对于频繁访问的数据，优先检查缓存
2. **数据分页**: 大数据量时使用分页获取，避免内存溢出
3. **异步处理**: 对于耗时操作，使用异步方式避免阻塞
4. **错误重试**: 网络请求失败时实现重试机制
5. **数据更新策略**: 根据数据时效性设置不同的缓存过期时间

## 扩展接口

### 自定义数据源
```python
class CustomDataSource:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_data(self, symbol: str) -> dict:
        # 自定义数据获取逻辑
        pass
```

### 插件系统
支持动态加载新的数据源和分析模块，提高扩展性。