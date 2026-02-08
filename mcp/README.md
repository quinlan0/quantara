# xtdata MCP服务器

基于HTTP的xtdata接口封装服务器，允许在没有xtdata的环境中通过REST API调用xtdata功能。实现了简化的MCP协议核心功能。

## 功能特性

- 🚀 **REST API**: 使用HTTP REST API进行通信
- 📊 **xtdata封装**: 封装xtdata库的核心接口
- 💰 **交易功能**: 支持实时交易操作（限价单、市价单、撤单等）
- 🔄 **JSON通信**: 基于JSON的请求/响应格式
- 🧪 **模拟模式**: 在没有xtdata的环境下提供模拟数据
- 🌐 **CORS支持**: 支持跨域请求

## 支持的接口

### HTTP端点

#### 1. `POST /tools/list`
列出可用工具

**响应**:
```json
{
  "tools": [
    {
      "name": "get_sector_list",
      "description": "获取板块列表",
      "inputSchema": {...}
    }
  ]
}
```

#### 2. `POST /tools/call`
调用工具

**请求格式**:
```json
{
  "name": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**响应格式**:
```json
{
  "result": {...}
}
```

或错误响应:
```json
{
  "error": "错误描述"
}
```

### 工具接口

#### 1. get_sector_list
获取板块列表

**参数**: 无

**返回值**: `List[str]` - 板块名称列表

#### 2. get_stock_list_in_sector
获取板块成份股

**参数**:
- `sector_name` (str): 板块名称
- `real_timetag` (int, 可选): 时间标签，默认-1

**返回值**: `List[str]` - 股票代码列表

#### 3. get_full_tick
获取盘口tick数据

**参数**:
- `code_list` (List[str]): 股票代码列表，格式如['000001.SZ', '600000.SH']

**返回值**: `Dict[str, Any]` - tick数据字典

#### 4. get_market_data_ex
获取市场数据

**参数**:
- `stock_list` (List[str]): 股票代码列表
- `period` (str, 可选): 周期，默认'1d'
- `count` (int, 可选): 获取数量，默认5
- 其他参数请参考xtdata文档

**返回值**: `Dict[str, Any]` - 市场数据字典

### 交易工具接口（需要启用 --enable-trade）

#### 1. get_account_positions
查看指定账户的持仓情况

**参数**: 无

**返回值**: `Dict[str, Any]` - 账户持仓信息
```json
{
  "account_id": "8887181228",
  "cash": 100000.0,
  "frozen_cash": 0.0,
  "market_value": 150000.0,
  "total_asset": 250000.0,
  "positions": [...],
  "positions_count": 5
}
```

#### 2. place_order
尝试挂单（限价单和市价单）

**参数**:
- `code` (str): 股票代码，如 '000001' 或 '000001.SH'
- `order_type` (str): 委托类型，'buy' 或 'sell'
- `volume` (int): 委托数量
- `price` (float, 可选): 委托价格（限价单必填）
- `price_type` (str, 可选): 报价类型，'limit' 或 'market'，默认'limit'

**返回值**: `Dict[str, Any]` - 挂单结果
```json
{
  "order_id": 123456,
  "code": "000001",
  "order_type": "buy",
  "volume": 1000,
  "price": 10.5,
  "price_type": "limit",
  "status": "submitted"
}
```

#### 3. query_orders
查询挂单成交情况

**参数**:
- `strategy_name` (str, 可选): 策略名称过滤
- `order_type` (str, 可选): 订单类型过滤，'buy' 或 'sell'
- `status_list` (List[str], 可选): 状态列表过滤

**返回值**: `Dict[str, Any]` - 订单查询结果
```json
{
  "orders": [...],
  "trades": [...],
  "orders_count": 5,
  "trades_count": 3
}
```

#### 4. cancel_order
撤单

**参数**:
- `order_id` (int): 订单ID

**返回值**: `Dict[str, Any]` - 撤单结果

## 快速开始

### 1. 启动服务器

```bash
# 数据查询模式（默认）
python mcp/run_server.py

# 启用交易功能（推荐用于生产环境）
python mcp/run_server.py --enable-trade \
  --trader-path "G:\国金证券QMT交易端\userdata_mini" \
  --account-id "8887181228"

# 完整配置（带认证）
python mcp/run_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --enable-trade \
  --xtdata-dir "G:\国金证券QMT交易端\datadir" \
  --trader-path "G:\国金证券QMT交易端\userdata_mini" \
  --account-id "8887181228" \
  --api-key "your-secret-api-key"
```

#### 交易功能参数说明

- `--enable-trade`: 启用交易功能
- `--trader-path`: 交易器数据目录路径（QMT的用户数据目录）
- `--account-id`: 交易账户ID
- `--session-id`: 交易会话ID（避免与其他策略冲突）

**⚠️ 安全提醒**: 启用交易功能时，请确保：
1. QMT交易终端正在运行
2. 账户资金充足
3. 网络连接稳定
4. 仅在测试环境验证功能

### 2. 认证配置

服务器支持API密钥认证，提供两种认证方式：

- **X-API-Key头**: `X-API-Key: your-secret-api-key`
- **Authorization头**: `Authorization: Bearer your-secret-api-key`

如果启动服务器时没有指定 `--api-key` 参数，则不启用认证，所有请求都可以访问。

### 2. 测试服务器

```bash
# 列出可用工具
curl -X POST http://localhost:8000/tools/list

# 数据查询接口
# 获取板块列表
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "get_sector_list", "arguments": {}}'

# 获取tick数据
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "get_full_tick", "arguments": {"code_list": ["000001.SZ", "600000.SH"]}}'

# 交易接口（需要启用--enable-trade）
# 查看持仓
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "get_account_positions", "arguments": {}}'

# 挂限价单（⚠️ 请谨慎使用）
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "place_order",
    "arguments": {
      "code": "000001",
      "order_type": "buy",
      "volume": 100,
      "price": 10.50,
      "price_type": "limit"
    }
  }'

# 查询订单
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "query_orders", "arguments": {}}'
```

### 3. 运行客户端演示

```bash
# 在另一个终端运行客户端演示
python mcp/client.py --demo
```

### 4. 交互式客户端

```bash
# 启动交互式客户端
python mcp/client.py

# 可用命令:
# sectors                    - 获取板块列表
# stocks <sector_name>       - 获取板块成份股
# tick <codes>               - 获取tick数据，如: tick 000001.SZ,600000.SH
# market <codes> [period]    - 获取市场数据，如: market 000001.SZ 1d
# tools                      - 列出可用工具
# quit                       - 退出
```

## Python客户端使用

```python
import os
from mcp.client import XtDataMCPClient

# 方法1：直接指定API密钥
client = XtDataMCPClient("http://localhost:9999", api_key="your-secret-api-key")

# 方法2：使用环境变量（推荐）
os.environ['XTDATA_MCP_API_KEY'] = 'your-secret-api-key'
client = XtDataMCPClient("http://localhost:9999")  # 会自动从环境变量读取

# 方法3：无认证（开发环境）
client = XtDataMCPClient("http://localhost:9999")  # 当服务器未启用认证时

# 使用客户端
sectors = client.get_sector_list()
tick_data = client.get_full_tick(["000001.SZ", "600000.SH"])
market_data = client.get_market_data_ex(["000001.SZ"], period="1d", count=5)
```

## 架构说明

```
┌─────────────────┐    HTTP/JSON    ┌─────────────────┐
│   MCP客户端     │◄──────────────► │  MCP服务器      │
│                 │                 │                 │
│ - 发送HTTP请求  │                 │ - 解析请求      │
│ - 解析JSON响应  │                 │ - 调用xtdata    │
└─────────────────┘                 └─────────────────┘
                                          │
                                          ▼
                                   ┌─────────────────┐
                                   │   xtdata库      │
                                   │                 │
                                   │ - get_sector_list│
                                   │ - get_full_tick │
                                   │ - etc...       │
                                   └─────────────────┘
```

## 开发说明

### 项目结构

```
mcp/
├── __init__.py          # 包初始化
├── server.py            # HTTP服务器实现
├── client.py            # Python客户端示例
├── run_server.py       # 服务器启动脚本
└── README.md            # 文档
```

### 添加新接口

1. 在 `server.py` 的 `XtDataService` 类中添加方法
2. 在 `MCPRequestHandler` 的 `_handle_list_tools` 中添加工具定义
3. 在 `_handle_call_tool` 中添加调用逻辑
4. 在客户端 `client.py` 中添加相应方法

### 错误处理

服务器捕获所有异常并返回标准JSON错误响应：

```json
{
  "error": "详细错误信息"
}
```

## 安全认证

服务器支持API密钥认证，确保只有授权客户端可以访问：

### 认证方式

1. **X-API-Key头**:
   ```
   X-API-Key: your-secret-api-key
   ```

2. **Authorization头** (Bearer Token):
   ```
   Authorization: Bearer your-secret-api-key
   ```

### API密钥设置方法

#### 1. 命令行参数（推荐用于脚本和CI/CD）

```bash
# 服务器启动
python mcp/run_server.py --api-key "my-secure-api-key-12345"

# 客户端连接
python mcp/client.py --api-key "my-secure-api-key-12345" --demo
```

#### 2. 环境变量（推荐用于生产环境）

```bash
# 设置环境变量
export XTDATA_MCP_API_KEY="my-secure-api-key-12345"

# 或者在Windows PowerShell中
$env:XTDATA_MCP_API_KEY="my-secure-api-key-12345"

# 然后启动服务器和客户端（无需指定--api-key）
python mcp/run_server.py
python mcp/client.py --demo
```

#### 3. 自动生成密钥

```bash
# 生成安全的随机密钥
python mcp/generate_key.py

# 生成指定类型的密钥
python mcp/generate_key.py --type hex --length 64

# 生成并显示环境变量设置命令
python mcp/generate_key.py --env
```

#### 4. 配置文件（适用于复杂配置）

```python
# 复制 config_example.py 为 config.py 并修改
from config import get_api_key

api_key = get_api_key()
# 在代码中使用
```

### 认证检查

- 如果服务器启动时未指定 `--api-key` 且环境变量未设置，则不启用认证
- 认证失败返回HTTP 401状态码和错误信息
- 支持的请求头：`X-API-Key` 或 `Authorization: Bearer <key>`
- 优先级：命令行参数 > 环境变量

## 注意事项

1. **xtdata依赖**: 未安装xtquant库时自动使用模拟模式
2. **数据目录**: 需要正确配置xtdata数据目录路径
3. **并发访问**: 当前实现每个请求处理一次，不支持并发
4. **CORS**: 服务器默认允许跨域请求
5. **端口占用**: 确保指定端口未被其他服务占用
6. **API密钥安全**: 在生产环境中使用强密码作为API密钥，避免硬编码在代码中

### 交易功能特别提醒

1. **风险警告**: 交易功能涉及真实资金操作，请谨慎使用
2. **环境要求**: 启用交易功能需要QMT交易终端正在运行
3. **账户安全**: 确保交易账户有足够资金，避免过度交易
4. **网络稳定**: 交易期间保持网络连接稳定，避免网络波动导致的交易失败
5. **测试环境**: 建议先在模拟环境测试所有功能
6. **权限控制**: 交易功能需要严格的API密钥认证
7. **日志记录**: 所有交易操作都会记录日志，便于追踪和审计

### 交易状态码说明

委托状态 (order_status):
- 48: 未报
- 50: 已报
- 55: 部成
- 56: 已成
- 54: 已撤
- 57: 废单

报价类型 (price_type):
- `xtconstant.FIX_PRICE`: 限价
- `xtconstant.LATEST_PRICE`: 最新价（市价）

## 许可证

本项目遵循与主项目相同的许可证。

my key:
gfGOo0@Q8thvwta0Z*j^mGQqWgIM4Yrn