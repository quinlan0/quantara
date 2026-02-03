# xtdata MCP服务器

基于HTTP的xtdata接口封装服务器，允许在没有xtdata的环境中通过REST API调用xtdata功能。实现了简化的MCP协议核心功能。

## 功能特性

- 🚀 **REST API**: 使用HTTP REST API进行通信
- 📊 **xtdata封装**: 封装xtdata库的核心接口
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

## 快速开始

### 1. 启动服务器

```bash
# 使用默认配置 (localhost:9999，无认证)
python mcp/run_server.py

# 指定主机和端口
python mcp/run_server.py --host 0.0.0.0 --port 8080

# 启用API密钥认证
python mcp/run_server.py --api-key "your-secret-api-key"

# 指定xtdata数据目录和认证
python mcp/run_server.py --xtdata-dir "G:\国金证券QMT交易端\datadir" --api-key "your-secret-api-key"
```

### 2. 认证配置

服务器支持API密钥认证，提供两种认证方式：

- **X-API-Key头**: `X-API-Key: your-secret-api-key`
- **Authorization头**: `Authorization: Bearer your-secret-api-key`

如果启动服务器时没有指定 `--api-key` 参数，则不启用认证，所有请求都可以访问。

### 2. 测试服务器

```bash
# 列出可用工具
curl -X POST http://localhost:8000/tools/list

# 获取板块列表
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "get_sector_list", "arguments": {}}'

# 获取tick数据
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "get_full_tick", "arguments": {"code_list": ["000001.SZ", "600000.SH"]}}'
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
from mcp.client import XtDataMCPClient

# 创建客户端（无认证）
client = XtDataMCPClient("http://localhost:9999")

# 创建客户端（带认证）
client = XtDataMCPClient("http://localhost:9999", api_key="your-secret-api-key")

# 获取板块列表
sectors = client.get_sector_list()
print(f"板块列表: {sectors}")

# 获取tick数据
tick_data = client.get_full_tick(["000001.SZ", "600000.SH"])
print(f"Tick数据: {tick_data}")

# 获取市场数据
market_data = client.get_market_data_ex(["000001.SZ"], period="1d", count=5)
print(f"市场数据: {market_data}")
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

### 启用认证

```bash
# 启动时指定API密钥
python mcp/run_server.py --api-key "my-secure-api-key-12345"

# 客户端使用认证
python mcp/client.py --api-key "my-secure-api-key-12345" --demo
```

### 认证检查

- 如果服务器启动时未指定 `--api-key`，则不启用认证
- 认证失败返回HTTP 401状态码
- 支持的请求头：`X-API-Key` 或 `Authorization`

## 注意事项

1. **xtdata依赖**: 未安装xtquant库时自动使用模拟模式
2. **数据目录**: 需要正确配置xtdata数据目录路径
3. **并发访问**: 当前实现每个请求处理一次，不支持并发
4. **CORS**: 服务器默认允许跨域请求
5. **端口占用**: 确保指定端口未被其他服务占用
6. **API密钥安全**: 在生产环境中使用强密码作为API密钥，避免硬编码在代码中

## 许可证

本项目遵循与主项目相同的许可证。