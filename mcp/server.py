#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP服务器 - xtdata接口封装

提供xtdata库接口的MCP封装，允许在没有xtdata的环境中通过MCP协议调用xtdata功能。
使用简化的HTTP服务器实现MCP协议的基本功能。
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import threading

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.utils import StockCodeUtils

try:
    from xtquant import xtdata
    from xtquant.xttrader import XtQuantTrader
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
except ImportError:
    raise ImportError("xtquant未安装，无法初始化MCP服务器")


class XtDataService:
    """xtdata服务封装"""

    def __init__(self, xtdata_dir: Optional[str] = None):
        """初始化服务"""
        # 配置xtdata
        if xtdata_dir:
            xtdata.data_dir = xtdata_dir
            xtdata.enable_hello = False
            print(f"已配置xtdata数据目录: {xtdata_dir}")

    def get_sector_list(self) -> List[str]:
        """获取板块列表"""
        try:
            return xtdata.get_sector_list() or []
        except Exception as e:
            print(f"获取板块列表失败: {e}")
            return []

    def get_stock_list_in_sector(self, sector_name: str, real_timetag: Union[str, int] = -1) -> List[str]:
        """获取板块成份股"""
        try:
            return xtdata.get_stock_list_in_sector(sector_name, real_timetag) or []
        except Exception as e:
            print(f"获取板块 {sector_name} 成份股失败: {e}")
            return []

    def get_full_tick(self, code_list: List[str]) -> Dict[str, Any]:
        """获取盘口tick数据"""
        try:
            return xtdata.get_full_tick(code_list) or {}
        except Exception as e:
            print(f"获取tick数据失败: {e}")
            return {}

    def get_market_data_ex(self, field_list: List[str], stock_list: List[str], period: str,
                          start_time: str, end_time: str, count: int,
                          dividend_type: str, fill_data: bool) -> Dict[str, Any]:
        """获取市场数据"""
        try:
            data_dict = xtdata.get_market_data_ex(
                field_list=field_list,
                stock_list=stock_list,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type=dividend_type,
                fill_data=fill_data
            )

            if data_dict is None:
                return {}

            # 将DataFrame转换为字典格式，便于JSON序列化
            result = {}
            for code, df in data_dict.items():
                if df is not None and not df.empty:
                    df['datetime'] = df.index
                    result[code] = df.to_dict('records')
                else:
                    result[code] = []

            return result

        except Exception as e:
            print(f"获取市场数据失败: {e}")
            return {}


class XtTradeService:
    """xttrade交易服务封装"""

    def __init__(self, xtdata_dir: Optional[str] = None, trader_path: Optional[str] = None,
                 session_id: int = 123456, account_id: str = '8887181228'):
        """初始化交易服务"""
        # 配置xtdata
        if xtdata_dir:
            xtdata.data_dir = xtdata_dir
            xtdata.enable_hello = False
            print(f"已配置xtdata数据目录: {xtdata_dir}")

        self.trader_path = trader_path or r'G:\国金证券QMT交易端\userdata_mini'
        self.session_id = session_id
        self.account_id = account_id

        # 交易相关对象
        self.trader = None
        self.account = None
        self.callback = None

        print(f"交易服务初始化完成: 路径={self.trader_path}, 账户={self.account_id}")

    def _init_trader(self):
        """初始化交易器"""
        if self.trader is not None:
            return True

        try:
            from common.utils import StockCodeUtils

            # 创建回调类
            class TraderCallback:
                def __init__(self):
                    self.logger = print  # 使用print作为简单日志

                def on_disconnected(self):
                    self.logger("交易连接断开")

                def on_stock_order(self, order):
                    self.logger(f"委托推送: {order.stock_code} {order.order_status}")

                def on_stock_trade(self, trade):
                    self.logger(f"成交推送: {trade.stock_code} {trade.traded_price}")

                def on_order_error(self, order_error):
                    self.logger(f"委托错误: {order_error.error_msg}")

                def on_cancel_error(self, cancel_error):
                    self.logger(f"撤单错误: {cancel_error.error_id}")

            # 创建交易器
            self.trader = XtQuantTrader(self.trader_path, self.session_id)
            account_type = 'STOCK' if self.account_id.startswith('8') else 'CREDIT'

            self.account = StockAccount(self.account_id, account_type)
            self.callback = TraderCallback()

            # 注册回调
            self.trader.register_callback(self.callback)

            # 启动交易线程
            self.trader.start()

            # 建立连接
            connect_result = self.trader.connect()
            if connect_result != 0:
                raise Exception(f"连接失败，错误码: {connect_result}")

            # 订阅账户
            subscribe_result = self.trader.subscribe(self.account)
            if subscribe_result != 0:
                raise Exception(f"订阅失败，错误码: {subscribe_result}")

            print("交易器初始化成功")
            return True

        except Exception as e:
            print(f"交易器初始化失败: {e}")
            return False

    def get_account_positions(self) -> Dict[str, Any]:
        """查看指定账户的持仓情况"""
        if not self._init_trader():
            return {"error": "交易器初始化失败"}

        try:
            # 获取持仓信息
            positions = self.trader.query_stock_positions(self.account)
            if positions is None:
                positions = []

            # 获取账户资产
            asset = self.trader.query_stock_asset(self.account)

            # 格式化持仓数据
            formatted_positions = []
            for pos in positions:
                if pos.volume <= 0 and pos.can_use_volume <= 0 and pos.on_road_volume <= 0:
                    continue

                formatted_positions.append({
                    'code': pos.stock_code[:6],  # 6位代码
                    'name': getattr(pos, 'stock_name', ''),  # 如果有的话
                    'volume': pos.volume,  # 总持仓
                    'can_use_volume': pos.can_use_volume,  # 可用数量
                    'avg_price': pos.avg_price,  # 成本价
                    'market_value': pos.market_value,  # 市值
                    'frozen_volume': pos.frozen_volume,  # 冻结数量
                    'on_road_volume': pos.on_road_volume,  # 在途数量
                })

            result = {
                'account_id': self.account_id,
                'cash': asset.cash if asset else 0,
                'frozen_cash': asset.frozen_cash if asset else 0,
                'market_value': asset.market_value if asset else 0,
                'total_asset': asset.total_asset if asset else 0,
                'positions': formatted_positions,
                'positions_count': len(formatted_positions)
            }

            return result

        except Exception as e:
            return {"error": f"获取持仓信息失败: {str(e)}"}

    def place_order(self, code: str, order_type: str, volume: int,
                   price: Optional[float] = None, price_type: str = "limit") -> Dict[str, Any]:
        """尝试挂单

        Args:
            code: 股票代码，如 '000001' 或 '000001.SH'
            order_type: 委托类型，'buy' 或 'sell'
            volume: 委托数量
            price: 委托价格（限价单必填，市价单可为空）
            price_type: 报价类型，'limit'（限价）或 'market'（市价）
        """
        if not self._init_trader():
            return {"error": "交易器初始化失败"}

        try:
            # 格式化代码
            formatted_code = StockCodeUtils.format_stock_codes_for_xtdata([code])[0]

            # 转换订单类型
            if order_type.lower() == 'buy':
                xt_order_type = xtconstant.STOCK_BUY
            elif order_type.lower() == 'sell':
                xt_order_type = xtconstant.STOCK_SELL
            else:
                return {"error": f"不支持的订单类型: {order_type}"}

            # 转换报价类型
            if price_type.lower() == 'limit':
                if price is None:
                    return {"error": "限价单必须指定价格"}
                xt_price_type = xtconstant.FIX_PRICE
                xt_price = price
            elif price_type.lower() == 'market':
                if order_type.lower() == 'buy':
                    xt_price_type = xtconstant.LATEST_PRICE
                    xt_price = 0  # 市价买单价格设为0
                else:
                    xt_price_type = xtconstant.LATEST_PRICE
                    xt_price = 1e6  # 市价卖单价格设为很高
            else:
                return {"error": f"不支持的报价类型: {price_type}"}

            # 挂单
            order_id = self.trader.order_stock(
                self.account,
                formatted_code,
                xt_order_type,
                volume,
                xt_price_type,
                xt_price,
                'mcp_trade',  # 策略名称
                f"mcp_{order_type}_{price_type}"  # 备注
            )

            if order_id == -1:
                return {"error": "挂单失败"}

            result = {
                'order_id': order_id,
                'code': code,
                'formatted_code': formatted_code,
                'order_type': order_type,
                'volume': volume,
                'price': price,
                'price_type': price_type,
                'status': 'submitted'
            }

            return result

        except Exception as e:
            return {"error": f"挂单失败: {str(e)}"}

    def query_orders(self, strategy_name: Optional[str] = None,
                    order_type: Optional[str] = None,
                    status_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """查询挂单成交情况"""
        if not self._init_trader():
            return {"error": "交易器初始化失败"}

        try:
            # 查询委托
            orders = self.trader.query_stock_orders(self.account, cancelable_only=False)
            if orders is None:
                orders = []

            # 查询成交
            trades = self.trader.query_stock_trades(self.account)
            if trades is None:
                trades = []

            # 格式化委托数据
            formatted_orders = []
            for order in orders:
                # 过滤条件
                if strategy_name and order.strategy_name != strategy_name:
                    continue
                if order_type:
                    if order_type.lower() == 'buy' and order.order_type != xtconstant.STOCK_BUY:
                        continue
                    if order_type.lower() == 'sell' and order.order_type != xtconstant.STOCK_SELL:
                        continue
                if status_list and order.order_status not in status_list:
                    continue

                formatted_orders.append({
                    'order_id': order.order_id,
                    'code': order.stock_code[:6],
                    'order_type': 'buy' if order.order_type == xtconstant.STOCK_BUY else 'sell',
                    'volume': order.order_volume,
                    'price': order.price,
                    'traded_volume': order.traded_volume,
                    'traded_price': order.traded_price,
                    'order_status': order.order_status,
                    'status_msg': order.status_msg,
                    'strategy_name': order.strategy_name,
                    'order_remark': order.order_remark,
                    'order_time': str(order.order_time) if hasattr(order, 'order_time') else None
                })

            # 格式化成交数据
            formatted_trades = []
            for trade in trades:
                if strategy_name and trade.strategy_name != strategy_name:
                    continue
                if order_type:
                    if order_type.lower() == 'buy' and trade.order_type != xtconstant.STOCK_BUY:
                        continue
                    if order_type.lower() == 'sell' and trade.order_type != xtconstant.STOCK_SELL:
                        continue

                formatted_trades.append({
                    'trade_id': trade.traded_id,
                    'order_id': trade.order_id,
                    'code': trade.stock_code[:6],
                    'order_type': 'buy' if trade.order_type == xtconstant.STOCK_BUY else 'sell',
                    'traded_volume': trade.traded_volume,
                    'traded_price': trade.traded_price,
                    'traded_amount': trade.traded_amount,
                    'strategy_name': trade.strategy_name,
                    'order_remark': trade.order_remark,
                    'traded_time': str(trade.traded_time) if hasattr(trade, 'traded_time') else None
                })

            result = {
                'orders': formatted_orders,
                'trades': formatted_trades,
                'orders_count': len(formatted_orders),
                'trades_count': len(formatted_trades)
            }

            return result

        except Exception as e:
            return {"error": f"查询订单失败: {str(e)}"}

    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """撤单"""
        if not self._init_trader():
            return {"error": "交易器初始化失败"}

        try:
            cancel_result = self.trader.cancel_order_stock(self.account, order_id)

            if cancel_result == 0:
                return {
                    'order_id': order_id,
                    'status': 'cancel_submitted',
                    'message': '撤单请求已提交'
                }
            else:
                return {
                    'order_id': order_id,
                    'status': 'cancel_failed',
                    'error_code': cancel_result,
                    'message': f'撤单失败，错误码: {cancel_result}'
                }

        except Exception as e:
            return {"error": f"撤单失败: {str(e)}"}


class MCPRequestHandler(BaseHTTPRequestHandler):
    """MCP HTTP请求处理器"""

    def __init__(self, *args, xtdata_service=None, trade_service=None, api_key=None, **kwargs):
        self.xtdata_service = xtdata_service
        self.trade_service = trade_service
        self.api_key = api_key
        super().__init__(*args, **kwargs)

    def _authenticate_request(self, headers: Dict[str, str]) -> bool:
        """验证请求认证"""
        if not self.api_key:
            # 如果没有设置API密钥，则允许所有请求
            return True

        # 检查API Key头
        api_key_header = headers.get('X-API-Key') or headers.get('X-Api-Key') or headers.get('Authorization')
        if api_key_header:
            # 如果是Bearer token格式
            if api_key_header.startswith('Bearer '):
                provided_key = api_key_header[7:]  # 去掉"Bearer "前缀
            else:
                provided_key = api_key_header

            return provided_key == self.api_key

        return False

    def do_POST(self):
        """处理POST请求"""
        try:
            # 认证检查
            if not self._authenticate_request(dict(self.headers)):
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('WWW-Authenticate', 'Bearer')
                self.end_headers()
                error_response = {"error": "Authentication required. Please provide X-API-Key header or Authorization header."}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return

            # 解析请求路径
            path = urllib.parse.urlparse(self.path).path

            # 处理不同类型的请求
            if path == "/tools/list":
                response = self._handle_list_tools()
            elif path == "/tools/call":
                # 读取请求体
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    request_data = json.loads(post_data.decode('utf-8'))
                else:
                    request_data = {}
                response = self._handle_call_tool(request_data)
            else:
                response = {"error": f"Unknown endpoint: {path}"}

            # 发送响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, Authorization')
            self.end_headers()

            self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2, default=str).encode('utf-8'))

        except Exception as e:
            self.send_error(500, str(e))

    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _handle_list_tools(self):
        """处理列出工具的请求"""
        tools = [
            {
                "name": "get_sector_list",
                "description": "获取板块列表",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_stock_list_in_sector",
                "description": "获取板块成份股",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sector_name": {
                            "type": "string",
                            "description": "板块名称"
                        },
                        "real_timetag": {
                            "type": ["string", "number"],
                            "description": "时间标签，可选，格式如'20171209'或时间戳",
                            "default": -1
                        }
                    },
                    "required": ["sector_name"]
                }
            },
            {
                "name": "get_full_tick",
                "description": "获取盘口tick数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code_list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "股票代码列表，格式如['000001.SZ', '600000.SH']"
                        }
                    },
                    "required": ["code_list"]
                }
            },
            {
                "name": "get_market_data_ex",
                "description": "获取市场数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "field_list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "字段列表，可选",
                            "default": []
                        },
                        "stock_list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "股票代码列表，格式如['000001.SZ', '600000.SH']"
                        },
                        "period": {
                            "type": "string",
                            "description": "周期，如'1d', '1m', '5m'等",
                            "default": "1d"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "开始时间，可选",
                            "default": ""
                        },
                        "end_time": {
                            "type": "string",
                            "description": "结束时间，可选",
                            "default": ""
                        },
                        "count": {
                            "type": "number",
                            "description": "获取数量，-1表示全部",
                            "default": -1
                        },
                        "dividend_type": {
                            "type": "string",
                            "description": "分红类型",
                            "default": "none"
                        },
                        "fill_data": {
                            "type": "boolean",
                            "description": "是否填充数据",
                            "default": True
                        }
                    },
                    "required": ["stock_list"]
                }
            }
        ]

        # 如果启用了交易功能，添加交易相关的工具
        if self.xtdata_service and hasattr(self, 'trade_service') and self.trade_service is not None:
            trade_tools = [
                {
                    "name": "get_account_positions",
                    "description": "查看指定账户的持仓情况",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "place_order",
                    "description": "尝试挂单（限价单和市价单）",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "股票代码，如 '000001' 或 '000001.SH'"
                            },
                            "order_type": {
                                "type": "string",
                                "description": "委托类型",
                                "enum": ["buy", "sell"]
                            },
                            "volume": {
                                "type": "integer",
                                "description": "委托数量"
                            },
                            "price": {
                                "type": "number",
                                "description": "委托价格（限价单必填，市价单可为空）",
                                "default": None
                            },
                            "price_type": {
                                "type": "string",
                                "description": "报价类型",
                                "enum": ["limit", "market"],
                                "default": "limit"
                            }
                        },
                        "required": ["code", "order_type", "volume"]
                    }
                },
                {
                    "name": "query_orders",
                    "description": "查询挂单成交情况",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "strategy_name": {
                                "type": "string",
                                "description": "策略名称过滤，可选",
                                "default": None
                            },
                            "order_type": {
                                "type": "string",
                                "description": "订单类型过滤，可选",
                                "enum": ["buy", "sell"],
                                "default": None
                            },
                            "status_list": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "状态列表过滤，可选",
                                "default": None
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "cancel_order",
                    "description": "撤单",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "integer",
                                "description": "订单ID"
                            }
                        },
                        "required": ["order_id"]
                    }
                }
            ]
            tools.extend(trade_tools)

        return {"tools": tools}

    def _handle_call_tool(self, request_data):
        """处理调用工具的请求"""
        tool_name = request_data.get("name")
        arguments = request_data.get("arguments", {})

        try:
            # xtdata工具
            if tool_name == "get_sector_list":
                result = self.xtdata_service.get_sector_list()
            elif tool_name == "get_stock_list_in_sector":
                result = self.xtdata_service.get_stock_list_in_sector(
                    arguments["sector_name"],
                    arguments.get("real_timetag", -1)
                )
            elif tool_name == "get_full_tick":
                result = self.xtdata_service.get_full_tick(arguments["code_list"])
            elif tool_name == "get_market_data_ex":
                result = self.xtdata_service.get_market_data_ex(
                    field_list=arguments.get("field_list", []),
                    stock_list=arguments["stock_list"],
                    period=arguments.get("period", "1d"),
                    start_time=arguments.get("start_time", ""),
                    end_time=arguments.get("end_time", ""),
                    count=arguments.get("count", -1),
                    dividend_type=arguments.get("dividend_type", "none"),
                    fill_data=arguments.get("fill_data", True)
                )
            # 交易工具
            elif tool_name == "get_account_positions":
                if not self.trade_service:
                    result = {"error": "交易功能未启用"}
                else:
                    result = self.trade_service.get_account_positions()
            elif tool_name == "place_order":
                if not self.trade_service:
                    result = {"error": "交易功能未启用"}
                else:
                    result = self.trade_service.place_order(
                        arguments["code"],
                        arguments["order_type"],
                        arguments["volume"],
                        arguments.get("price"),
                        arguments.get("price_type", "limit")
                    )
            elif tool_name == "query_orders":
                if not self.trade_service:
                    result = {"error": "交易功能未启用"}
                else:
                    result = self.trade_service.query_orders(
                        arguments.get("strategy_name"),
                        arguments.get("order_type"),
                        arguments.get("status_list")
                    )
            elif tool_name == "cancel_order":
                if not self.trade_service:
                    result = {"error": "交易功能未启用"}
                else:
                    result = self.trade_service.cancel_order(arguments["order_id"])
            else:
                result = {"error": f"未知工具: {tool_name}"}

            return {"result": result}

        except Exception as e:
            return {"error": f"调用工具 {tool_name} 时出错: {str(e)}"}

    def log_message(self, format, *args):
        """重写日志方法，减少输出"""
        pass


class XtDataMCPServer:
    """xtdata MCP服务器"""

    def __init__(self, host: str = "localhost", port: int = 8000, xtdata_dir: Optional[str] = None,
                 api_key: Optional[str] = None, enable_trade: bool = False,
                 trader_path: Optional[str] = None, session_id: int = 123456,
                 account_id: str = '8887181228'):
        self.host = host
        self.port = port
        self.xtdata_service = XtDataService(xtdata_dir)
        self.api_key = api_key

        # 交易服务
        self.enable_trade = enable_trade
        if enable_trade:
            self.trade_service = XtTradeService(xtdata_dir, trader_path, session_id, account_id)
        else:
            self.trade_service = None

        self.server = None
        self.server_thread = None

    def start(self):
        """启动服务器"""
        def create_handler(*args, **kwargs):
            return MCPRequestHandler(*args, xtdata_service=self.xtdata_service, trade_service=self.trade_service, api_key=self.api_key, **kwargs)

        self.server = HTTPServer((self.host, self.port), create_handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        print(f"xtdata MCP服务器已启动: http://{self.host}:{self.port}")
        print("支持的接口:")
        print("  POST /tools/list - 列出可用工具")
        print("  POST /tools/call - 调用工具")

        if self.enable_trade:
            print("\n🔥 交易功能已启用")
            print("  支持的交易工具:")
            print("  - get_account_positions: 查看持仓")
            print("  - place_order: 挂单（限价/市价）")
            print("  - query_orders: 查询订单")
            print("  - cancel_order: 撤单")
        else:
            print("\n📊 仅数据查询模式（无交易功能）")
            print("  如需启用交易功能，请使用 --enable-trade 参数")

        print("\n按Ctrl+C停止服务器")

    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("服务器已停止")

    def serve_forever(self):
        """持续运行服务器"""
        try:
            self.start()
            # 保持主线程运行
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到停止信号...")
            self.stop()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='xtdata MCP服务器')
    parser.add_argument('--host', type=str, default='localhost',
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8000,
                       help='服务器端口')
    parser.add_argument('--xtdata-dir', type=str,
                       default=r'G:\国金证券QMT交易端\datadir',
                       help='xtdata数据目录路径')
    parser.add_argument('--enable-trade', action='store_true',
                       help='启用交易功能')
    parser.add_argument('--trader-path', type=str,
                       default=r'G:\国金证券QMT交易端\userdata_mini',
                       help='交易器数据目录路径')
    parser.add_argument('--session-id', type=int, default=123456,
                       help='交易会话ID')
    parser.add_argument('--account-id', type=str, default='18887181228',
                       help='交易账户ID')
    parser.add_argument('--api-key', type=str,
                       help='API密钥，用于认证')

    args = parser.parse_args()

    # 创建并启动服务器
    server = XtDataMCPServer(
        host=args.host,
        port=args.port,
        xtdata_dir=args.xtdata_dir,
        enable_trade=args.enable_trade,
        trader_path=args.trader_path,
        session_id=args.session_id,
        account_id=args.account_id,
        api_key=args.api_key
    )

    if args.enable_trade:
        print("⚠️  已启用交易功能，请确保交易环境配置正确")
        print(f"   交易路径: {args.trader_path}")
        print(f"   账户ID: {args.account_id}")

    server.serve_forever()


if __name__ == "__main__":
    main()