# 金融数据分析智能体 - 使用示例

## 基础数据获取示例

### 获取股票日K线数据

```python
import pandas as pd
from financial_data_agent import StockDataFetcher

# 初始化数据获取器
fetcher = StockDataFetcher(cache_enabled=True)

# 获取单只股票的历史数据
stock_data = fetcher.get_daily_kline(
    symbol='000001.SZ',  # 平安银行
    start_date='2024-01-01',
    end_date='2024-12-31'
)

print(stock_data.head())
# 输出:
#          date   open   high    low  close    volume
# 0  2024-01-01  10.50  10.80  10.45  10.75  12345678
# 1  2024-01-02  10.75  10.90  10.60  10.85  15678901
# ...
```

### 获取多只股票数据

```python
# 批量获取股票数据
symbols = ['000001.SZ', '600000.SH', '000002.SZ']
batch_data = fetcher.get_batch_daily_kline(
    symbols=symbols,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 返回字典格式，每个股票对应一个DataFrame
for symbol, data in batch_data.items():
    print(f"{symbol}: {len(data)} 条记录")
```

### 获取实时行情数据

```python
# 获取实时报价
real_time_data = fetcher.get_real_time_quote([
    '000001.SZ',  # 平安银行
    '600000.SH',  # 浦发银行
    '000002.SZ'   # 万科A
])

print(real_time_data)
# 输出:
# {
#     '000001.SZ': {
#         'price': 10.85,
#         'change': 0.15,
#         'change_pct': 1.40,
#         'volume': 12345678,
#         'amount': 134567890.12,
#         'timestamp': '2024-12-31 15:00:00'
#     },
#     ...
# }
```

## 板块分析示例

### 分析行业板块

```python
from financial_data_agent import SectorAnalyzer

analyzer = SectorAnalyzer()

# 获取行业板块列表
industries = analyzer.get_industry_boards()
print("主要行业板块:")
for industry in industries[:10]:
    print(f"- {industry['name']}: {industry['stock_count']} 只股票")

# 分析特定行业板块
industry_analysis = analyzer.analyze_industry_sector('银行')

print(f"银行板块分析结果:")
print(f"- 板块内股票数量: {industry_analysis['stock_count']}")
print(f"- 平均市盈率: {industry_analysis['avg_pe']:.2f}")
print(f"- 总市值: {industry_analysis['total_market_cap']:.2f} 亿元")
print(f"- 领涨股票: {industry_analysis['leading_stocks']}")
```

### 概念板块分析

```python
# 获取概念板块数据
concepts = analyzer.get_concept_boards()

# 分析热门概念板块
hot_concepts = analyzer.get_hot_concepts(limit=10)
for concept in hot_concepts:
    print(f"{concept['name']}: 涨跌幅 {concept['change_pct']:.2f}%")

# 深度分析特定概念
ai_concept = analyzer.analyze_concept_sector('人工智能')

print("人工智能概念板块分析:")
print(f"- 概念强度: {ai_concept['strength_score']:.2f}")
print(f"- 相关股票: {len(ai_concept['related_stocks'])} 只")
print(f"- 资金流入: {ai_concept['fund_flow']:.2f} 亿元")
```

## 图论关系分析示例

### 构建股票关系网络

```python
from financial_data_agent import StockNetworkAnalyzer
import matplotlib.pyplot as plt

network_analyzer = StockNetworkAnalyzer()

# 构建股票关系网络
network_analyzer.build_stock_network(
    stocks=['000001.SZ', '600000.SH', '000002.SZ', '600036.SH'],
    include_industries=True,
    include_concepts=True
)

# 分析股票相关性
correlations = network_analyzer.analyze_stock_correlations(
    time_window='1M',  # 1个月
    correlation_threshold=0.6
)

print("高度相关的股票对:")
for pair, corr in correlations.items():
    stock1, stock2 = pair
    print(f"{stock1} - {stock2}: 相关系数 {corr:.3f}")
```

### 板块关系图谱

```python
# 构建板块关系图
sector_graph = network_analyzer.build_sector_relationship_graph()

# 找到最具影响力的板块
influential_sectors = network_analyzer.find_influential_sectors(top_n=5)

print("最具影响力的板块:")
for sector, score in influential_sectors.items():
    print(f"{sector}: 影响力分数 {score:.2f}")

# 分析板块间的关联
sector_connections = network_analyzer.analyze_sector_connections()

print("板块关联分析:")
for sector, connections in sector_connections.items():
    print(f"{sector} 关联的板块: {connections}")
```

## 基本面数据分析示例

### 获取财务指标

```python
from financial_data_agent import FundamentalAnalyzer

fundamental = FundamentalAnalyzer()

# 获取公司财务数据
financial_data = fundamental.get_company_financials(
    symbol='000001.SZ',
    report_type='annual',  # annual, quarterly
    periods=3  # 最近3期
)

print("平安银行财务指标:")
for period, data in financial_data.items():
    print(f"{period}:")
    print(f"  营收: {data['revenue']:.2f} 亿元")
    print(f"  净利润: {data['net_profit']:.2f} 亿元")
    print(f"  ROE: {data['roe']:.2f}%")
```

### 财务比率分析

```python
# 计算财务比率
ratios = fundamental.calculate_financial_ratios('000001.SZ')

print("财务比率分析:")
print(f"市盈率 (PE): {ratios['pe_ratio']:.2f}")
print(f"市净率 (PB): {ratios['pb_ratio']:.2f}")
print(f"股息率: {ratios['dividend_yield']:.2f}%")
print(f"净利率: {ratios['net_margin']:.2f}%")

# 同行比较
peer_comparison = fundamental.compare_with_peers(
    symbol='000001.SZ',
    industry='银行'
)

print("同行比较:")
print(f"PE相对估值: {peer_comparison['pe_percentile']:.1f}%")
print(f"ROE排名: {peer_comparison['roe_rank']}")
```

## 新闻和情绪分析示例

### 获取市场新闻

```python
from financial_data_agent import NewsAnalyzer

news_analyzer = NewsAnalyzer()

# 获取最新市场新闻
latest_news = news_analyzer.get_latest_news(
    categories=['A股', '港股', '美股'],
    limit=20
)

print("最新市场新闻:")
for news in latest_news[:5]:
    print(f"- {news['title']}")
    print(f"  来源: {news['source']}")
    print(f"  发布时间: {news['publish_time']}")
    print(f"  情感评分: {news['sentiment_score']:.2f}")
```

### 新闻情感分析

```python
# 分析新闻情感对市场的影响
sentiment_analysis = news_analyzer.analyze_market_sentiment(
    time_window='1D',  # 1天
    symbols=['000001.SZ', '600000.SH']
)

print("市场情感分析:")
for symbol, sentiment in sentiment_analysis.items():
    print(f"{symbol}:")
    print(f"  整体情感: {sentiment['overall_sentiment']}")
    print(f"  正面新闻数: {sentiment['positive_news_count']}")
    print(f"  负面新闻数: {sentiment['negative_news_count']}")
    print(f"  情感强度: {sentiment['sentiment_intensity']:.2f}")
```

## 缓存优化示例

### 使用缓存装饰器

```python
from financial_data_agent import cached, CACHE_DIR
import os

# 配置缓存目录
os.environ['FINANCIAL_CACHE_DIR'] = '/tmp/cache_output/quantara'

@cached(expire_hours=1)  # 1小时缓存
def get_frequent_data(symbol):
    # 耗时的网络请求
    return fetch_from_api(symbol)

# 第一次调用 - 从API获取
data1 = get_frequent_data('000001.SZ')

# 第二次调用 - 从缓存获取（如果在1小时内）
data2 = get_frequent_data('000001.SZ')
```

### 批量数据缓存

```python
from financial_data_agent import BatchDataCache

cache = BatchDataCache()

# 缓存批量数据
batch_data = {
    'stocks': stock_data,
    'indices': index_data,
    'sectors': sector_data
}

cache.save_batch_data('market_snapshot', batch_data, expire_hours=4)

# 稍后加载缓存的数据
cached_data = cache.load_batch_data('market_snapshot')
if cached_data:
    print("使用缓存的数据")
else:
    print("缓存已过期，需要重新获取")
```

## 性能优化示例

### 异步数据获取

```python
import asyncio
from financial_data_agent import AsyncDataFetcher

async def fetch_multiple_symbols():
    fetcher = AsyncDataFetcher()

    symbols = ['000001.SZ', '600000.SH', '000002.SZ', '600036.SH']

    # 并发获取多个股票数据
    results = await fetcher.get_multiple_stocks_async(
        symbols=symbols,
        data_type='daily_kline',
        start_date='2024-01-01',
        end_date='2024-12-31'
    )

    print(f"成功获取 {len(results)} 只股票的数据")

    # 计算相关性矩阵
    correlation_matrix = fetcher.calculate_correlation_matrix(results)
    print("股票相关性矩阵:")
    print(correlation_matrix)

# 运行异步函数
asyncio.run(fetch_multiple_symbols())
```

### 内存优化处理

```python
from financial_data_agent import MemoryOptimizer

optimizer = MemoryOptimizer()

# 处理大数据文件
large_dataset = optimizer.load_large_dataset(
    file_path='large_market_data.csv',
    chunk_size=50000  # 每次处理5万行
)

# 优化DataFrame内存使用
optimized_df = optimizer.optimize_dataframe_memory(large_dataset)

print(f"内存优化: {optimizer.get_memory_savings():.2f} MB 已节省")

# 分块处理
results = optimizer.process_in_chunks(
    data=large_dataset,
    process_func=my_analysis_function,
    chunk_size=10000
)
```

## 完整工作流程示例

### 量化策略数据准备

```python
from financial_data_agent import QuantDataPipeline

# 初始化量化数据管道
pipeline = QuantDataPipeline()

# 配置策略参数
config = {
    'universe': ['000001.SZ', '600000.SH', '000002.SZ'],  # 股票池
    'start_date': '2023-01-01',
    'end_date': '2024-12-31',
    'indicators': ['MA5', 'MA20', 'RSI', 'MACD'],  # 技术指标
    'fundamental_factors': ['PE', 'PB', 'ROE', 'ROA']  # 基本面因子
}

# 执行完整数据准备流程
quant_data = pipeline.prepare_quantitative_data(config)

print("量化数据准备完成:")
print(f"- 股票数量: {len(quant_data['price_data'])}")
print(f"- 日期范围: {quant_data['date_range']}")
print(f"- 技术指标: {list(quant_data['technical_indicators'].keys())}")
print(f"- 基本面因子: {list(quant_data['fundamental_factors'].keys())}")

# 生成特征矩阵
feature_matrix = pipeline.create_feature_matrix(quant_data)

print(f"特征矩阵形状: {feature_matrix.shape}")
print(f"特征数量: {len(pipeline.get_feature_names())}")
```

### 风险分析和组合优化

```python
from financial_data_agent import PortfolioAnalyzer

portfolio_analyzer = PortfolioAnalyzer(quant_data)

# 计算风险指标
risk_metrics = portfolio_analyzer.calculate_portfolio_risk(
    weights=[0.4, 0.4, 0.2],  # 投资权重
    confidence_level=0.95
)

print("投资组合风险分析:")
print(f"预期年化收益率: {risk_metrics['expected_return']:.2f}%")
print(f"年化波动率: {risk_metrics['annual_volatility']:.2f}%")
print(f"VaR (95%置信度): {risk_metrics['var_95']:.2f}%")
print(f"最大回撤: {risk_metrics['max_drawdown']:.2f}%")

# 优化投资组合
optimal_weights = portfolio_analyzer.optimize_portfolio(
    target_return=0.15,  # 目标收益率15%
    risk_free_rate=0.03  # 无风险利率3%
)

print("最优投资组合权重:")
for symbol, weight in optimal_weights.items():
    print(f"{symbol}: {weight:.2f}")
```