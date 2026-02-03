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

try:
    from xtquant import xtdata
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


class MCPRequestHandler(BaseHTTPRequestHandler):
    """MCP HTTP请求处理器"""

    def __init__(self, *args, xtdata_service=None, api_key=None, **kwargs):
        self.xtdata_service = xtdata_service
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
        return {
            "tools": [
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
        }

    def _handle_call_tool(self, request_data):
        """处理调用工具的请求"""
        tool_name = request_data.get("name")
        arguments = request_data.get("arguments", {})

        try:
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
                 api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.xtdata_service = XtDataService(xtdata_dir)
        self.api_key = api_key
        self.server = None
        self.server_thread = None

    def start(self):
        """启动服务器"""
        def create_handler(*args, **kwargs):
            return MCPRequestHandler(*args, xtdata_service=self.xtdata_service, api_key=self.api_key, **kwargs)

        self.server = HTTPServer((self.host, self.port), create_handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        print(f"xtdata MCP服务器已启动: http://{self.host}:{self.port}")
        print("支持的接口:")
        print("  POST /tools/list - 列出可用工具")
        print("  POST /tools/call - 调用工具")
        print("按Ctrl+C停止服务器")

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

    args = parser.parse_args()

    # 创建并启动服务器
    server = XtDataMCPServer(args.host, args.port, args.xtdata_dir)
    server.serve_forever()


if __name__ == "__main__":
    main()