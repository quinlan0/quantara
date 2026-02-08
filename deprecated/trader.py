#coding=utf-8
import sqlite3
import datetime
from enum import Enum
from utils import transform_code, STR_FORMAT

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant

class OrderStatus(Enum):
    INVALID = -1
    TRYOPEN = 0
    OPEN = 1
    TRYCLOSE = 2
    CLOSE = 3
    TRYCANCEL = 4
    CANCEL = 5

def trans_timestamp(t_int):
    dt = datetime.datetime.fromtimestamp(t_int)
    return dt

class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def __init__(self, logger=None):
        self.logger = logger

    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        self.logger.error("connection lost")
        
    def on_stock_order(self, order):
        """
        委托回报推送
        :return:
        """
        order_id = order.order_id  
        updated_info = dict()
        now = datetime.datetime.now()
        if order.order_status == xtconstant.ORDER_REPORTED:
            if order.order_type == xtconstant.STOCK_BUY:
                updated_info['open_order_id'] = order_id
                updated_info['open_order_time'] = now
                updated_info['open_order_price'] = order.price
                updated_info['open_order_volume'] = order.order_volume
                updated_info['open_reason'] = f"{order.strategy_name}_{order.order_remark}"
                updated_info['status'] = OrderStatus.TRYOPEN.value
            elif order.order_type == xtconstant.STOCK_SELL:
                updated_info['close_order_id'] = order_id
                updated_info['close_order_time'] = now
                updated_info['close_order_price'] = order.price
                updated_info['close_order_volume'] = order.order_volume 
                updated_info['close_reason'] = f"{order.strategy_name}_{order.order_remark}"
                updated_info['status'] = OrderStatus.TRYCLOSE.value
        elif order.order_status == xtconstant.ORDER_SUCCEEDED:
            if order.order_type == xtconstant.STOCK_BUY:
                updated_info['status'] = OrderStatus.OPEN.value
                updated_info['open_order_id'] = order_id
                updated_info['open_traded_time'] = now
                updated_info['open_traded_price'] = order.traded_price
                updated_info['open_traded_volume'] = order.traded_volume 
            elif order.order_type == xtconstant.STOCK_SELL:
                updated_info['status'] = OrderStatus.CLOSE.value
                updated_info['close_order_id'] = order_id
                updated_info['close_traded_time'] = now
                updated_info['close_traded_price'] = order.traded_price
                updated_info['close_traded_volume'] = order.traded_volume
        elif order.order_status == xtconstant.ORDER_PART_SUCC:
            if order.order_type == xtconstant.STOCK_BUY:
                updated_info['open_order_id'] = order_id
                updated_info['open_traded_time'] = now
                updated_info['open_traded_price'] = order.traded_price
                updated_info['open_traded_volume'] = order.traded_volume
            elif order.order_type == xtconstant.STOCK_SELL:
                updated_info['close_order_id'] = order_id
                updated_info['close_traded_time'] = now
                updated_info['close_traded_price'] = order.traded_price
                updated_info['close_traded_volume'] = order.traded_volume
        self.logger.info(f"on order callback:code({order.stock_code}), status({order.order_status}), set_str({set_str})")
        
    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        self.logger.info(f"on trade callback:account({trade.account_id}), code({trade.stock_code}), order_id({trade.order_id})")
        
    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        self.logger.error("on order_error callback: order_id({}), error_id({}), msg({})".format(order_error.order_id, order_error.error_id, order_error.error_msg))
        
    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        self.logger.error(f"on cancel_error callback: order_id({cancel_error.order_id}), error({cancel_error.error_id}), msg({cancel_error.error_msg})")
        
    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        self.logger.error(f"on_order_stock_async_response: account({response.account_id}), order_id({response.order_id}), seq({response.seq})")
        
    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        self.logger.error(f"on_account_status: account({status.account_id}),account_type({status.account_type}), status({status.status})")

class Trader(object):
    def __init__(self, logger, enable_trader=False, strategy_name="test", session_id=123456):
        self.acc, self.trader, self.callback = None, None, None
        self.strategy_name = strategy_name
        self.logger = logger
        if enable_trader:
            self.acc, self.trader, self.callback = self.InitTrader(logger=logger, session_id=session_id)
        
    def InitTrader(self, logger, session_id=123456):
        # path为mini qmt客户端安装目录下userdata_mini路径
        path='G:\\国金证券QMT交易端\\userdata_mini'
        # session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号
        trader = XtQuantTrader(path, session_id)
        # 创建资金账号，StockAccount可以用第二个参数指定账号类型，如沪港通传'HUGANGTONG'，深港通传'SHENGANGTONG'
        my_count = '8887181228'
        acc = StockAccount(my_count, 'STOCK')
        # 创建交易回调类对象，并声明接收回调
        callback = MyXtQuantTraderCallback(logger)
        trader.register_callback(callback)
        # 启动交易线程
        trader.start()
        # 建立交易连接，返回0表示连接成功
        connect_result = trader.connect()
        if connect_result != 0:
            assert False, f"connection result {connect_result} is invalid!"
        # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
        subscribe_result = trader.subscribe(acc)
        if subscribe_result != 0:
            assert False, f"subscribe result {subscribe_result} is invalid!"
        logger.info("Trader initialized!")
        return acc, trader, callback

    def query_orders(self, cancelable_only=True, strategy_name=None, order_type=None, status_list=None):
        raw_orders = self.trader.query_stock_orders(self.acc, cancelable_only)
        orders = list()
        for order in raw_orders:
            if strategy_name is not None:
                if order.strategy_name != strategy_name:
                    continue
            if status_list is not None:
                if order.order_status not in status_list:
                    continue
            if order_type is not None:
                if order.order_type != order_type:
                    continue
            orders.append({
                'stock_code': order.stock_code,
                'order_type': order.order_type,
                'order_id': order.order_id,
                'order_sysid': order.order_sysid,
                'order_time': trans_timestamp(order.order_time),
                'order_price': order.price,
                'order_volume': order.order_volume,
                'traded_price': order.traded_price,
                'traded_volume': order.traded_volume,
                'order_status': order.order_status,
                'status_msg': order.status_msg,
                'strategy_name': order.strategy_name,
                'order_remark': order.order_remark
            })
        return orders

    def query_trades(self, strategy_name=None, order_type=None):
        raw_trades = self.trader.query_stock_trades(self.acc)
        trades = list()
        for trade in raw_trades:
            if strategy_name is not None:
                if trade.strategy_name != strategy_name:
                    continue
            if order_type is not None:
                if trade.order_type != order_type:
                    continue
            trades.append({
                'stock_code': trade.stock_code,
                'order_type': trade.order_type,
                'traded_id': trade.traded_id,
                'traded_time': trans_timestamp(trade.traded_time),
                'traded_volume': trade.traded_volume,
                'traded_price': trade.traded_price,
                'traded_amount': trade.traded_amount,
                'order_id': trade.order_id,
                'order_sysid': trade.order_sysid,
                'strategy_name': trade.strategy_name,
                'order_remark': trade.order_remark
            })
        return trades

    def query_positions(self):
        '''
        account_type	int	账号类型，参见数据字典
        account_id	str	资金账号
        stock_code	str	证券代码
        volume	int	持仓数量
        can_use_volume	int	可用数量
        open_price	float	开仓价
        market_value	float	市值
        frozen_volume	int	冻结数量
        on_road_volume	int	在途股份
        yesterday_volume	int	昨夜拥股
        avg_price	float	成本价
        '''
        positions = dict()
        for pos in self.trader.query_stock_positions(self.acc):
            code = pos.stock_code[0:6]
            if pos.volume <= 0 and pos.can_use_volume <= 0 and pos.on_road_volume <= 0:
                continue
            positions[code] = {
                'code': code,
                'volume': pos.volume,
                'can_use_volume': pos.can_use_volume,
                'open_price': pos.open_price,
                'market_value': pos.market_value,
                'frozen_volume': pos.frozen_volume,
                'on_road_volume': pos.on_road_volume,
                'yesterday_volume': pos.yesterday_volume,
                'avg_price': pos.avg_price
            }
        return positions
        
    def account_info(self):
        account = self.trader.query_account_infos()[0]
        asset = self.trader.query_stock_asset(self.acc)
        account_info = dict()
        account_info['account_type'] = account.account_type
        account_info['account_id'] = account.account_id
        account_info['login_status'] = account.login_status
        account_info['cash'] = asset.cash
        account_info['frozen_cash'] = asset.frozen_cash
        account_info['market_value'] = asset.market_value
        account_info['total_asset'] = asset.total_asset
        return account_info
        
    def try_open(self, code, price, volume, reason=""):
        # price_type = xtconstant.LATEST_PRICE / xtconstant.FIX_PRICE
        price_type = xtconstant.FIX_PRICE
        order_id = self.trader.order_stock(self.acc, transform_code(code), xtconstant.STOCK_BUY, volume, price_type, price, self.strategy_name, reason)
        if order_id == -1:
            self.logger.error("Can not buy, order_id -1")
        return order_id
            
    def try_latest_price_open(self, code, volume, reason=""):
        price_type = xtconstant.LATEST_PRICE
        order_id = self.trader.order_stock(self.acc, transform_code(code), xtconstant.STOCK_BUY, volume, price_type, 0, self.strategy_name, reason)
        if order_id == -1:
            self.logger.error("Can not buy, order_id -1")
        return order_id
            
    def try_close(self, code, price, volume, reason=""):
        # price_type = xtconstant.LATEST_PRICE / xtconstant.FIX_PRICE
        price_type = xtconstant.FIX_PRICE
        order_id = self.trader.order_stock(self.acc, transform_code(code), xtconstant.STOCK_SELL, volume, price_type, price, self.strategy_name, reason)
        if order_id == -1:
            self.logger.error("Can not sell, order_id -1")
        return order_id
        
    def try_latest_price_close(self, code, volume, reason=""):
        price_type = xtconstant.LATEST_PRICE
        order_id = self.trader.order_stock(self.acc, transform_code(code), xtconstant.STOCK_SELL, volume, price_type, 1e6, self.strategy_name, reason)
        if order_id == -1:
            self.logger.error("Can not sell, order_id -1")
        return order_id

    def cancel_order(self, order_id):
        cancel_result = self.trader.cancel_order_stock(self.acc, order_id)
        if cancel_result != 0:
            self.logger.error(f"Order ({order_id}) can not be cancelled!")