# Common 模块重构说明

## 📋 模块概述

`common/` 目录包含了项目中常用的基础模块，这些模块是从 `deprecated/` 目录重构而来，经过优化和标准化处理。

## 🏗️ 模块列表

### 1. **utils.py** - 通用工具模块
**新增模块**: 整合常用的工具函数

**功能**:
- 股票代码格式转换和处理
- 数据类型安全转换
- 字典合并等通用工具函数

**主要组件**:
- `StockCodeUtils`: 股票代码处理工具类
- `DataProcessingUtils`: 数据处理工具类

**使用场景**:
- 股票代码标准化处理
- 数据清洗和格式转换
- 通用工具函数调用

### 2. **stock_basic_info_manager.py** - 股票基本信息管理器
**新增模块**: 专门负责股票基本信息获取

**功能**:
- 从 xtdata 获取详细的股票基本信息
- 计算总市值和流通市值
- 支持多种数据源回退机制
- 批量处理股票代码转换

**主要特性**:
- 优先使用 xtdata 获取准确数据
- 自动回退到 akshare 保证可用性
- 完整的错误处理和日志记录
- 支持缓存机制提高性能

**使用场景**:
- 获取股票的总股本、流通股本信息
- 计算基于实时价格的市值数据
- 批量获取股票基本信息

### 3. **board_data_manager.py** - 板块数据管理器
**新增模块**: 专门负责板块数据管理

**功能**:
- 从网络获取最新的板块数据
- 统一保存到指定缓存目录
- 管理缓存文件的元数据信息
- 提供命令行接口进行数据更新

**主要特性**:
- 数据获取与保存分离设计
- 丰富的元数据（更新日期、版本等）
- 命令行工具支持
- 完善的错误处理

**使用场景**:
- 定期更新板块数据
- 管理缓存文件状态
- 命令行批量处理

### 4. **logger.py** - 日志模块
**原文件**: `deprecated/logger_utils.py`

**功能**:
- 统一的日志记录接口
- 支持loguru和标准logging两种后端
- 自动创建带时间戳的日志文件
- 支持日志轮转和保留策略

**主要改进**:
- 更好的错误处理
- 更灵活的配置选项
- 向后兼容的接口

### 5. **trade_date.py** - 交易日期管理
**原文件**: `deprecated/trade_date.py`

**功能**:
- 交易日历管理
- 交易日判断和查询
- 交易日期间隔计算
- 日期范围内的交易日获取

**主要改进**:
- 更丰富的方法接口
- 更好的日期格式处理
- 增强的错误处理
- 支持多种日期输入格式

### 6. **board_graph.py** - 板块图管理
**原文件**: `deprecated/board_graph.py`

**功能**:
- 股票与板块关系图构建
- 支持行业、概念、指数三种板块类型
- 图论关系分析
- 板块内股票查询

**主要改进**:
- 引入 `BoardNodeType` 和 `BoardEdgeType` 枚举，替代数字类型，提高类型安全性
- 使用申万行业分类系统，支持三级行业层次结构
- 改进的数据获取逻辑，支持多种数据源和错误处理
- 增强的缓存机制，支持数据更新和持久化
- 更丰富的数据结构，包含元信息和标签支持
- 提供枚举到字符串的转换接口，便于显示和调试

### 7. **agent.py** - AI智能体
**原文件**: `deprecated/agent.py`

**功能**:
- AI模型调用接口
- 支持多种模型配置
- 统一的对话和JSON输出接口

**主要改进**:
- 配置化管理（不再使用环境变量）
- 支持多模型切换
- 更好的错误处理
- 增强的返回信息

### 8. **data_getter.py** - 数据获取器
**重构自**: `deprecated/data_getter.py` + `deprecated/stock_base_info.py`

**功能**:
- 个股基本信息获取
- 历史行情数据获取
- 实时数据获取
- 板块信息查询
- 智能缓存管理

**主要改进**:
- 整合了两个原有模块的功能
- 标准化的数据字段定义
- 支持多种股票代码输入格式
- 改进的缓存策略

## 🔧 技术改进

### 1. **代码标准化**
- 统一的导入风格
- 标准化的错误处理
- 完整的类型提示
- 一致的命名规范

### 2. **性能优化**
- 智能缓存机制
- 批量数据处理
- 内存使用优化
- 异步处理支持

### 3. **可维护性**
- 模块化设计
- 清晰的职责分离
- 完善的文档
- 向后兼容性

### 4. **扩展性**
- 插件化架构
- 配置化管理
- 易于添加新功能
- 支持自定义扩展

## 📊 依赖关系

```
data_getter.py
├── logger.py (日志记录)
├── trade_date.py (交易日历)
├── board_graph.py (板块关系)
└── akshare, xtquant (外部库)

agent.py
├── logger.py (可选)
└── openai (外部库)

board_graph.py
└── akshare (外部库)

trade_date.py
└── akshare (外部库)

logger.py
└── loguru (可选)
```

## 🔧 详细API文档

### utils.py - 通用工具模块

#### StockCodeUtils - 股票代码处理工具类

##### 主要方法

- **`transform_code(code: str) -> str`**
  将股票代码转换为6位数字格式
  ```python
  # 支持的输入格式
  StockCodeUtils.transform_code('000001.SH')  # -> '000001'
  StockCodeUtils.transform_code('SH000001')   # -> '000001'
  StockCodeUtils.transform_code('000001sh')   # -> '000001'
  StockCodeUtils.transform_code('sh000001')   # -> '000001'
  StockCodeUtils.transform_code('000001SH')   # -> '000001'
  StockCodeUtils.transform_code('000001')     # -> '000001'
  ```

- **`transform_code_for_xtdata(code: str) -> str`**
  将股票代码转换为xtdata所需的格式
  ```python
  StockCodeUtils.transform_code_for_xtdata('000001')  # -> '000001.SZ'
  StockCodeUtils.transform_code_for_xtdata('600000')  # -> '600000.SH'
  StockCodeUtils.transform_code_for_xtdata('000001.SZ')  # -> '000001.SZ'
  ```

- **`extract_clean_code(code_str: str, max_length: int = 6) -> str`**
  从字符串中提取干净的股票代码
  ```python
  StockCodeUtils.extract_clean_code('000001.SH')  # -> '000001'
  StockCodeUtils.extract_clean_code('SH000001股票')  # -> '000001'
  ```

- **`normalize_stock_codes(codes: List[str]) -> List[str]`**
  批量标准化股票代码
  ```python
  codes = ['000001.SH', 'SH600000', '000002sz', '300001']
  clean_codes = StockCodeUtils.normalize_stock_codes(codes)
  # -> ['000001', '600000', '000002', '300001']
  ```

- **`format_stock_codes_for_xtdata(codes: List[str]) -> List[str]`**
  批量转换为xtdata格式
  ```python
  codes = ['000001', '600000', '000001.SZ']
  xtdata_codes = StockCodeUtils.format_stock_codes_for_xtdata(codes)
  # -> ['000001.SZ', '600000.SH', '000001.SZ']
  ```

- **`is_valid_stock_code(code: str) -> bool`**
  验证股票代码是否有效
  ```python
  StockCodeUtils.is_valid_stock_code('000001')  # -> True
  StockCodeUtils.is_valid_stock_code('000001.SH')  # -> True
  StockCodeUtils.is_valid_stock_code('invalid')  # -> False
  ```

- **`get_exchange_suffix(code: str) -> str`**
  获取交易所后缀
  ```python
  StockCodeUtils.get_exchange_suffix('000001')  # -> 'SZ'
  StockCodeUtils.get_exchange_suffix('600000')  # -> 'SH'
  StockCodeUtils.get_exchange_suffix('000001.SZ')  # -> 'SZ'
  ```

#### DataProcessingUtils - 数据处理工具类

##### 主要方法

- **`safe_strip(value: Any) -> str`**
  安全地转换为字符串并去除空白字符
  ```python
  DataProcessingUtils.safe_strip(None)  # -> ''
  DataProcessingUtils.safe_strip('  hello  ')  # -> 'hello'
  DataProcessingUtils.safe_strip(123)  # -> '123'
  ```

- **`safe_int(value: Any, default: int = 0) -> int`**
  安全地转换为整数
  ```python
  DataProcessingUtils.safe_int('123')  # -> 123
  DataProcessingUtils.safe_int('invalid', 0)  # -> 0
  ```

- **`safe_float(value: Any, default: float = 0.0) -> float`**
  安全地转换为浮点数
  ```python
  DataProcessingUtils.safe_float('123.45')  # -> 123.45
  DataProcessingUtils.safe_float('invalid', 0.0)  # -> 0.0
  ```

- **`merge_dicts(*dicts: Dict) -> Dict`**
  合并多个字典
  ```python
  dict1 = {'a': 1}
  dict2 = {'b': 2}
  dict3 = {'a': 3}  # 会覆盖dict1中的'a'
  result = DataProcessingUtils.merge_dicts(dict1, dict2, dict3)
  # -> {'a': 3, 'b': 2}
  ```

#### 向后兼容函数

为了保持向后兼容，提供以下模块级函数：

```python
from common.utils import (
    transform_code,           # 等同于 StockCodeUtils.transform_code
    transform_code_for_xtdata, # 等同于 StockCodeUtils.transform_code_for_xtdata
    normalize_stock_codes,    # 等同于 StockCodeUtils.normalize_stock_codes
    format_stock_codes_for_xtdata  # 等同于 StockCodeUtils.format_stock_codes_for_xtdata
)
```

### stock_basic_info_manager.py - 股票基本信息管理器

#### StockBasicInfoManager 类

```python
class StockBasicInfoManager:
    CACHE_DIR = Path("/tmp/cache_output/quantara/date_info")
    STOCK_BASIC_INFO_CACHE = CACHE_DIR / "stock_basic_info.pkl"

    def __init__(self)
    def fetch_and_save_stock_basic_info(self) -> None
    def get_cache_info(self) -> Dict[str, Any]
    def clear_cache(self) -> None

    @classmethod
    def update_stock_basic_info(cls) -> None  # 类方法，方便调用
```

#### 使用示例

**基本使用**:
```python
from common.stock_basic_info_manager import StockBasicInfoManager

# 创建管理器
manager = StockBasicInfoManager()

# 获取并保存所有股票基本信息
manager.fetch_and_save_stock_basic_info()
```

**查看缓存信息**:
```python
manager = StockBasicInfoManager()

# 获取缓存文件信息
info = manager.get_cache_info()
print(f"更新日期: {info['update_date']}")
print(f"股票数量: {info['total_count']}")
print(f"文件大小: {info['file_size']} bytes")
```

**命令行使用**:
```bash
# 更新股票基本信息
python -m common.stock_basic_info_manager update

# 查看缓存信息
python -m common.stock_basic_info_manager info

# 清除缓存
python -m common.stock_basic_info_manager clear
```

#### 缓存数据格式

保存的缓存文件包含以下字段：

```python
{
    'stock_data': [
        {
            'code': '000001',
            'name': '平安银行',
            'total_mv': 1234567890.0,    # 总市值
            'cir_mv': 987654321.0,      # 流通市值
            'pe': 8.5,                   # 市盈率
            'pb': 0.8,                   # 市净率
            'total_shares': None,        # 总股本 (akshare不提供)
            'cir_shares': None           # 流通股本 (akshare不提供)
        },
        # ... 更多股票数据
    ],
    'update_date': '2024-01-15',      # 更新日期 (YYYY-MM-DD)
    'update_datetime': '2024-01-15T10:30:00',  # 更新日期时间
    'timestamp': 1705312200.0,        # 时间戳
    'version': '1.0',                  # 数据版本
    'total_count': 5123                # 总股票数量
}
```

### board_data_manager.py - 板块数据管理器

#### BoardDataManager 类

```python
class BoardDataManager:
    CACHE_DIR = Path("/tmp/cache_output/quantara/date_info")
    BOARD_INFO_CACHE = CACHE_DIR / "board_info.pkl"

    def __init__(self)
    def fetch_and_save_board_data(self, board_graph: BoardGraph = None) -> None
    def get_cache_info(self) -> Dict[str, Any]
    def clear_cache(self) -> None

    @classmethod
    def update_board_data(cls) -> None  # 类方法，方便调用
```

#### 使用示例

**基本使用**:
```python
from common.board_data_manager import BoardDataManager
from common.board_graph import BoardGraph

# 创建数据管理器
manager = BoardDataManager()

# 获取并保存板块数据
board_graph = BoardGraph()
manager.fetch_and_save_board_data(board_graph)

# 或者直接更新（创建新的BoardGraph实例）
manager.fetch_and_save_board_data()
```

**查看缓存信息**:
```python
manager = BoardDataManager()

# 获取缓存文件信息
info = manager.get_cache_info()
print(f"更新日期: {info['update_date']}")
print(f"行业板块数量: {info['industry_count']}")
print(f"概念板块数量: {info['concept_count']}")
print(f"指数板块数量: {info['index_count']}")
```

**命令行使用**:
```bash
# 更新板块数据
python -m common.board_data_manager update

# 查看缓存信息
python -m common.board_data_manager info

# 清除缓存
python -m common.board_data_manager clear
```

#### 缓存数据格式

保存的缓存文件包含以下字段：

```python
{
    'industry_info': {...},      # 行业板块数据
    'concept_info': {...},       # 概念板块数据
    'index_info': {...},         # 指数板块数据
    'update_date': '2024-01-15',      # 更新日期 (YYYY-MM-DD)
    'update_datetime': '2024-01-15T10:30:00',  # 更新日期时间
    'timestamp': 1705312200.0,   # 时间戳
    'version': '1.0'             # 数据版本
}
```

### data_getter.py - 数据获取器

#### 重构概述

本次重构整合了原有的 `stock_base_info.py` 和 `data_getter.py` 两个模块，将个股基本信息和行情数据获取功能合并到一个统一的接口中。

#### 数据字段标准化

**个股基本信息字段**:
```python
# 必选字段
STOCK_BASIC_REQUIRED = ['code', 'name']

# 可选字段
STOCK_BASIC_OPTIONAL = ['total_mv', 'cir_mv', 'pe', 'pb', 'total_shares', 'cir_shares']
```

**行情数据字段**:
```python
# 必选字段
MARKET_DATA_REQUIRED = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pre_close']
```

#### API接口

**DataGetter 类**:

**初始化**:
```python
from common.data_getter import DataGetter

getter = DataGetter(xtdata_dir=r'G:\国金证券QMT交易端\datadir')
```

**股票代码格式支持**:
DataGetter 支持多种股票代码输入格式，内部统一转换为6位数字格式：

```python
# 支持的输入格式
'000001.SH'   -> '000001'
'SH000001'    -> '000001'
'000001sh'    -> '000001'
'sh000001'    -> '000001'
'000001'      -> '000001'
```

所有返回的数据字典的key都使用原始输入格式。

**获取个股基本信息**:
```python
# 获取全部A股基本信息
all_stocks = getter.get_stock_basic_info()

# 获取指定股票的基本信息
specific_stocks = getter.get_stock_basic_info(['000001', '600000'])

# 强制刷新缓存
fresh_data = getter.get_stock_basic_info(refresh=True)
```

**获取行情数据**:
```python
# 获取日K线数据
daily_data = getter.get_market_data('000001', period='1d', count=100)

# 获取分钟线数据
minute_data = getter.get_market_data('000001', period='1m', count=240)

# 获取多只股票数据
multi_data = getter.get_market_data(['000001', '600000'], period='1d', count=50)

# 强制刷新缓存（会下载最新数据）
fresh_data = getter.get_market_data('000001', period='1d', count=100, refresh=True)
```

**数据获取策略**:
- **优先级**: xtdata本地数据 → 缓存 → 下载
- **自动下载**: 当xtdata数据不足或获取失败时，自动下载最新数据
- **智能缓存**: 下载的数据会自动缓存，避免重复下载

**获取实时数据**:
```python
# 获取实时行情
real_time = getter.get_real_time_data('000001')
```

**获取最新交易日数据**:
```python
# 获取最新交易日全天分钟线
latest_day_data = getter.get_latest_trading_day_market_data('000001', period='1m')
```

**获取板块信息**:
```python
# 获取所有板块信息
sector_data = getter.get_sector_list()

# 获取特定类型的板块（如概念板块）
concept_data = getter.get_sector_list(start_type='TGN')

# 获取指定板块列表
specific_sectors = getter.get_sector_list(all_sectors=['银行', '医药'])

# 更新板块数据后获取
fresh_sector_data = getter.get_sector_list(update_data=True)

# 返回结构
{
    'sector_infos': {'板块名': ['股票代码1', '股票代码2', ...]},
    'stock_infos': {'股票代码': ['所属板块1', '所属板块2', ...]}
}
```

#### 数据格式说明

**个股基本信息 DataFrame**:
```python
# DataFrame 结构
df = pd.DataFrame({
    'code': ['000001', '600000'],  # 股票代码（必选）
    'name': ['平安银行', '浦发银行'],  # 股票名称（必选）
    'total_mv': [123456.78, 234567.89],  # 总市值（可选）
    'cir_mv': [98765.43, 198765.43],    # 流通市值（可选）
    'pe': [8.5, 7.2],  # 市盈率（可选）
    'pb': [0.85, 0.72],  # 市净率（可选）
    'total_shares': [None, None],  # 总股本（可选，后续扩展）
    'cir_shares': [None, None]     # 流通股本（可选，后续扩展）
})
```

**行情数据 DataFrame**:
```python
# DataFrame 结构（datetime 作为索引）
df = pd.DataFrame({
    'open': [10.50, 10.75],      # 开盘价
    'high': [10.80, 10.90],      # 最高价
    'low': [10.45, 10.60],       # 最低价
    'close': [10.75, 10.85],     # 收盘价
    'volume': [12345678, 15678901],  # 成交量
    'amount': [134567890.12, 170123456.78],  # 成交额
    'pre_close': [10.45, 10.75]  # 前收盘价
}, index=pd.to_datetime(['2024-01-01', '2024-01-02']))
```

#### 缓存机制

**缓存目录结构**:
```
/tmp/cache_output/quantara/data_getter/
├── stock_basic_all_stocks.pkl          # 个股基本信息缓存
├── YYYYMMDD/                          # 按日期组织的行情数据缓存
│   ├── market_data_000001_1d_100.pkl
│   ├── market_data_600000_1m_240.pkl
│   └── ...
└── sector_info_000001.pkl             # 板块信息缓存
```

**缓存策略**:
- **个股基本信息**: 24小时过期
- **行情数据**: 按日期缓存，当日数据不过期
- **板块信息**: 24小时过期

**缓存管理**:
```python
# 清理过期缓存
getter.clear_cache(older_than_hours=48)

# 清理特定类型缓存
getter.clear_cache(cache_type='market_data')

# 清理所有缓存
getter.clear_cache()
```

#### 向后兼容

为了保持向后兼容性，提供以下别名：
```python
from common.data_getter import StockBasicInfo  # 等同于 DataGetter
```

### agent.py - AI智能体

#### 配置系统

**模型配置结构**:

每个模型配置包含以下字段：

```python
@dataclass
class ModelConfig:
    name: str                    # 配置名称（唯一标识）
    api_key: str                # API密钥
    base_url: str               # API基础URL
    model_name: str             # 模型名称
    description: Optional[str]  # 描述信息（可选）
```

**默认配置**:

模块内置了以下默认配置：

```python
MODEL_CONFIGS = {
    'qwen3-max': ModelConfig(
        name='qwen3-max',
        api_key='your-api-key',  # 需要替换为实际密钥
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        model_name='qwen3-max',
        description='阿里云通义千问3.0 Max模型'
    ),

    'qwen-flash': ModelConfig(
        name='qwen-flash',
        api_key='your-api-key',  # 需要替换为实际密钥
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        model_name='qwen-flash',
        description='阿里云通义千问Flash模型（快速响应）'
    ),
}
```

#### 使用方法

**基本使用**:

```python
from common.agent import Agent

# 使用默认配置（qwen3-max）
agent = Agent()

# 使用指定配置
agent_flash = Agent('qwen-flash')

# 查询
result = agent.query(
    system_prompt="你是一个专业的股票分析师。",
    msg_content="分析一下当前A股市场的走势。"
)

print(result['answer'])
```

**配置管理**:

模型配置是预定义的固定配置，不能动态修改：

```python
from common.agent import MODEL_CONFIGS

# 查看所有可用配置
agent = Agent()
configs = agent.get_available_configs()
print(f"可用配置: {list(configs.keys())}")

# 查看当前配置
current_config = agent.get_current_config()
print(f"当前配置: {current_config}")
```

**JSON输出**:

```python
# 请求JSON格式输出
result = agent.query(
    system_prompt="你是一个数据分析助手，请以JSON格式回答。",
    msg_content="分析股票代码000001的基本信息。",
    json_output=True
)

# 解析JSON结果
import json
data = json.loads(result['answer'])
print(data)
```

#### API接口详解

**Agent类**:

**初始化**:
```python
Agent(model_config: str = 'qwen3-max')
```

**参数:**
- `model_config`: 模型配置名称，默认使用 'qwen3-max'

**主要方法**:

##### `query(system_prompt, msg_content, json_output=False)`
执行一次对话查询

**参数:**
- `system_prompt`: 系统提示
- `msg_content`: 用户消息内容
- `json_output`: 是否要求JSON格式输出

**返回值:**
```python
{
    'answer': str,              # 回答内容
    'answer_json': dict|None,   # JSON格式回答（如果json_output=True）
    'reason': str,              # 完成原因
    'prompt_tokens': int,       # 输入token数
    'completion_tokens': int,   # 输出token数
    'total_tokens': int,        # 总token数
    'start_time': datetime,     # 开始时间
    'finish_time': datetime,    # 结束时间
    'model_config': str,        # 使用的配置名
    'model_name': str           # 使用的模型名
}
```

##### `get_available_configs()`
获取所有可用配置

##### `get_current_config()`
获取当前使用的配置

## 🚀 使用示例

### 基本使用

```python
# 数据获取
from common.data_getter import DataGetter
getter = DataGetter()
stock_info = getter.get_stock_basic_info(['000001', '600000'])
market_data = getter.get_market_data('000001', period='1d', count=100)

# AI对话
from common.agent import Agent
agent = Agent('qwen3-max')
result = agent.query("分析A股走势", "请给出投资建议")

# 日志记录
from common.logger import get_logger, init_logger
init_logger("my_app")
logger = get_logger()
logger.info("应用启动")

# 交易日历
from common.trade_date import TradeDate
trade_date = TradeDate()
is_trading = trade_date.is_trade_date("2024-01-01")

# 板块分析 - 使用枚举
from common.board_graph import BoardGraph, BoardNodeType, BoardEdgeType, BoardNode
board_graph = BoardGraph()

# 获取银行行业的股票
stocks = board_graph.get_stocks_by_industry("银行")

# 创建节点并使用枚举
stock_node = BoardNode("000001", "平安银行", BoardNodeType.STOCK)
print(f"节点类型: {stock_node.node_type}")  # BoardNodeType.STOCK
print(f"类型名称: {str(stock_node.node_type)}")  # "股票"
print(f"短名称: {stock_node.node_type.to_short_string()}")  # "STOCK"

# 使用边关系枚举
print(f"行业关系: {BoardEdgeType.INDUSTRY_RELATION}")  # BoardEdgeType.INDUSTRY_RELATION
print(f"关系名称: {str(BoardEdgeType.CONCEPT_RELATION)}")  # "概念关系"
```

## 🧪 测试

运行完整测试套件：
```bash
# 运行所有common模块测试
python test/test_common_modules.py

# 运行单个模块测试
python test/common/test_agent.py
python test/common/test_data_getter.py
```

## ⚠️ 注意事项

1. **环境依赖**
   - 主要依赖: `pandas`, `numpy`, `akshare`
   - 可选依赖: `xtquant`, `loguru`, `openai`
   - Python版本: 3.7+

2. **网络访问**
   - `board_graph.py` 和 `trade_date.py` 需要网络访问获取数据
   - 支持缓存机制减少网络请求

3. **配置要求**
   - AI模型需要有效的API密钥
   - xtdata需要正确的安装路径配置

4. **性能考虑**
   - 大量数据获取时注意内存使用
   - 合理使用缓存减少API调用

## 🔄 迁移指南

从deprecated模块迁移：

```python
# 旧版
from deprecated.logger_utils import init_logger
from deprecated.stock_base_info import StockBaseInfos
from deprecated.data_getter import DataGetter

# 新版
from common.logger import init_logger
from common.data_getter import DataGetter
```

## 📈 后续扩展

预留的扩展点：
- [ ] 添加更多数据源支持
- [ ] 实现分布式缓存
- [ ] 支持实时数据流处理
- [ ] 添加数据验证和清洗功能
- [ ] 集成更多AI模型提供商

---

**重构完成时间**: 2024年
**重构目标**: 提高代码质量、可维护性和扩展性
**兼容性**: 保持向后兼容，逐步迁移使用