import argparse
import datetime
import time
from pathlib import Path
from tqdm import tqdm
import numpy as np
import pandas as pd

from utils import root_dir, STR_FORMAT, validate_trade_time

from common.utils import cache_output, load_data
from common.logger_utils import init_logger, logger
from common.new_data_getter import DataGetter
from notification.feishu import FeiShu
from trader import Trader, OrderStatus
from trader_db import DB
from tick_data_db import TickDB

from xtquant import xtdata
from xtquant import xtconstant
import xtquant
xtdata.data_dir = 'G:\\国金证券QMT交易端\\datadir'
xtdata.enable_hello = False
# xtdata.reconnect()

trader = None
feishu = None

def show_positions(trader):
    logger.info("Positions:")
    positions = trader.query_positions()
    position_infos = dict()
    for position in positions:
        code = position.stock_code[0:6]
        position_infos[code] = {
            'code_wm': position.stock_code,
            'volume': position.volume,
            'price': position.avg_price
        }
        logger.info(position_infos[code])
    logger.info(list(position_infos.keys()))
    
def calculate_features(tick_data):
    import talib 
    prices = tick_data['price'].to_numpy()
    tick_data['mean_50'] = talib.SMA(prices, timeperiod=50)
    tick_data['mean_100'] = talib.SMA(prices, timeperiod=100)
    macd_fast_p = 40
    macd_slow_p = 80
    macd_signal_p = 20
    tick_data['macd'], tick_data['macdsignal'], tick_data['macdhist'] = talib.MACD(prices, fastperiod=macd_fast_p, slowperiod=macd_slow_p, signalperiod=macd_signal_p)
    bband_time_p = 50
    bband_dev_up = 2.0
    bband_dev_dn = 2.0
    tick_data['bband_upper'], tick_data['bband_mid'], tick_data['bband_lower'] = talib.BBANDS(prices, timeperiod=bband_time_p, nbdevup=bband_dev_up, nbdevdn=bband_dev_dn)
    rsi_p = 14
    tick_data['rsi'] = talib.RSI(prices, timeperiod=rsi_p)
    return tick_data

def manual_buy(code, tick_data, cash, expected_price):
    global trader, feishu
    if cash < 5000.0:
        logger.error("Cash {:.2f} is invalid!".format(cash))
        return
    cur_tick = tick_data.iloc[-1]
    now = datetime.datetime.now()
    volume = manual_info['volume']
    if manual_info['price'] is None:
        info_str = "MANUAL_BUY_ORDER@{}, volume({})".format(now.time(), volume)
        trader.try_latest_price_open(code, volume, reason='manual_buy')
    else:
        price = manual_info['price']
        if abs(price - cur_tick['price']) > 0.01:
            logger.error(" manual price({:.3f}) is large difference with cur price({:.3f})".format(price, cur_tick['price']))
            return
        info_str = "MANUAL_BUY_ORDER@{}, price({:.3f}), volume({})".format(now.time(), price, volume)
        trader.try_open(code, price, volume, reason="manual_buy")
    logger.info(info_str)
    feishu.send_user_message(info_str, target=1)

def manual_sell(code, tick_data, manual_info):
    global trader, feishu
    if 'opened_trade_id' not in manual_info:
        logger.error(" No opened traded_id in manual_info")
        return
    cur_tick = tick_data.iloc[-1]
    now = datetime.datetime.now()
    volume = manual_info['volume']
    opened_trade_id = manual_info['opened_trade_id']
    if manual_info['price'] is None:
        info_str = "MANUAL_SELL_ORDER@{}, volume({})".format(now.time(), volume)
        trader.try_latest_price_close(code, volume, reason=str(opened_trade_id))
    else:
        price = manual_info['price']
        if abs(price - cur_tick['price']) > 0.01:
            logger.error(" manual price({:.3f}) is large difference with cur price({:.3f})".format(price, cur_tick['price']))
            return
        info_str = "MANUAL_SELL_ORDER@{}, price({:.3f}), volume({})".format(now.time(), price, volume)
        trader.try_close(code, price, volume, reason=str(opened_trade_id))
    logger.info(info_str)
    feishu.send_user_message(info_str, target=1)
    
def handle_try_open_order(code, order, tick_data):
    global trader, feishu
    order_time, order_price, order_volume = order['order_time'], order['order_price'], order['order_volume']
    now = datetime.datetime.now()
    delta_dt = now - order_time
    delta_seconds = delta_dt.total_seconds()
    if delta_seconds > 120:
        trader.cancel_order(order['order_id'])
        info_str = "CANCEL@{}, try open order_id({}) delta_seconds ({})".format(now.time(), order['order_id'], delta_seconds)
        logger.error(info_str)
        feishu.send_user_message(info_str, target=1)
        
def handle_try_close_order(code, order, tick_data):
    global trader, feishu
    order_time, order_price, order_volume = order['order_time'], order['order_price'], order['order_volume']
    now = datetime.datetime.now()
    delta_dt = now - order_time 
    delta_seconds = delta_dt.total_seconds()
    if delta_seconds > 120:
        trader.cancel_order(order['order_id'])
        info_str = "CANCEL@{}, try close order_id({})".format(now.time(), order['order_id'])
        logger.error(info_str)
        feishu.send_user_message(info_str, target=1)
    if len(tick_data) > 0:
        cur_tick = tick_data.iloc[-1]
        if cur_tick['price'] <= order_price - 0.001:
            trader.cancel_order(order['order_id'])
            trader.try_latest_price_close(code, order_volume, reason=order['order_remark'])
            info_str = "SELL_ORDER_NOW@{}, cur_tick_price({:.3f}), volume({})".format(now.time(), cur_tick['price'], order_volume)
            logger.error(info_str)
            feishu.send_user_message(info_str, target=1)
    
def get_opened_trades(trader, strategy_name):
    order_dict = dict()
    
    # 收集正在selling的order
    selling_orders = trader.query_orders(cancelable_only=True, strategy_name=strategy_name, order_type=xtconstant.STOCK_SELL)
    for order in selling_orders:
        order_dict[order['order_remark']] = order
    # 收集已经sell的trade
    selled_trades = trader.query_trades(strategy_name=strategy_name, order_type=xtconstant.STOCK_SELL)
    for trade in selled_trades:
        order_dict[trade['order_remark']] = trade

    opened_trades = list()
    raw_opened_trades = trader.query_trades(strategy_name=strategy_name, order_type=xtconstant.STOCK_BUY)
    for trade in raw_opened_trades:
        if str(trade['order_id']) in order_dict:
            continue
        opened_trades.append(trade)
    return opened_trades

   
def run_once(strategy_name, code, tick_data_db, trader, manual_info):
    now = datetime.datetime.now()
    logger.info(f"Handle bar @ {now.strftime(STR_FORMAT)}")
    if not validate_trade_time(now):
        logger.error(" Not in time range!")
        return
    # query tick_data
    # time_range = [datetime.datetime(2025, 4, 10, 9, 30, 0), datetime.datetime(2025, 4, 10, 10, 30, 0)]
    time_range = [None, now]
    all_tick_data = tick_data_db.get_tick_data(code=code, time_range=time_range)
    if len(all_tick_data) < 20:
        logger.info("  tick data size is less than 20")
        return
    tick_data = all_tick_data
    if len(all_tick_data) > 300:
        tick_data = all_tick_data.iloc[-300:].copy()
    # calcualte feature
    tick_data = calculate_features(tick_data)
    
    account_info = trader.account_info()
    cash, frozen_cash = account_info['cash'], account_info['frozen_cash']   
    logger.info("Cash {:.2f} ,frozen cash {:.2f}".format(cash, frozen_cash))

    # 优先分析已有order
    last_open_order_time = None
    buying_orders = trader.query_orders(strategy_name=strategy_name, cancelable_only=True, 
                                        order_type=xtconstant.STOCK_BUY, 
                                        status_list=[xtconstant.ORDER_REPORTED])
    logger.info(f"Handle Buying Orders({len(buying_orders)})")
    for order in buying_orders:
        logger.info(f"  - {order}")
        #handle_try_open_order(code, order, tick_data)
        last_open_order_time = max(order['order_time'], last_open_order_time) if last_open_order_time is not None else order['order_time']
    
    selling_orders = trader.query_orders(strategy_name=strategy_name, cancelable_only=True,
                                         order_type=xtconstant.STOCK_SELL,
                                         status_list=[xtconstant.ORDER_REPORTED])
    logger.info(f"Handle Selling Orders({len(selling_orders)})")
    for order in selling_orders:
        #handle_try_close_order(code, order, tick_data)
        logger.info(f"  - {order}")

    opened_trades = get_opened_trades(trader, strategy_name)
    logger.info(f"Handle Opened Trades({len(opened_trades)})")
    for trade in opened_trades:
        last_open_order_time = max(trade['traded_time'], last_open_order_time) if last_open_order_time is not None else trade['traded_time']
        logger.info(f"  - {trade}")

    if manual_info is not None:
        if manual_info['type'] == xtconstant.STOCK_BUY:
            logger.info(f"Handle Manual Buy Signal")
            manual_buy(code, tick_data, cash, manual_info)
        elif manual_info['type'] == xtconstant.STOCK_SELL:
            logger.info(f"Handle Manual Sell Signal")
            manual_sell(code, tick_data, manual_info)

            
if __name__ == "__main__":
    strat_name = 'etf_buyer_0418'
    init_logger(strat_name, "/tmp/{}".format("test"))
    feishu = FeiShu()
    data_dir = Path("/tmp") / "cache_output"
    
    # show_positions(trader)
    
    code = '159792'
    name = '港互联网'
    
    dt = datetime.datetime.now()
    dt_str = dt.strftime("%Y%m%d")

    # load tick_data db
    tick_data_db_path = data_dir / "tick_data_db" / f"tick_data_{dt_str}.db"
    if not tick_data_db_path.exists():
        logger.error(f"Tick Data DB ({tick_data_db_path}) is not existed!")
    tick_data_db = TickDB(tick_data_db_path)

    # load order_info_db
    trader = Trader(logger, enable_trader=True, strategy_name=strat_name, session_id=123450)

    # manual
    manual_info = None
    manual_info = {'type': xtconstant.STOCK_BUY, 'price': 0.769, 'volume': 10000}
    #manual_info = {'type': xtconstant.STOCK_BUY, 'price': None, 'volume': 10000}
    #manual_info = {'type': xtconstant.STOCK_SELL, 'price': 0.771, 'volume': 10000, 'opened_trade_id': 1090569125}
    #manual_info = {'type': xtconstant.STOCK_SELL, 'price': None, 'volume': 10000}
    run_once(strat_name, code, tick_data_db, trader, manual_info)
