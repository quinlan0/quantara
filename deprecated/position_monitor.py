import argparse
import datetime
import time
import pickle
from pathlib import Path
from tqdm import tqdm
import numpy as np
import pandas as pd

from utils import root_dir, STR_FORMAT

from common.utils import cache_output, load_data
from common.logger_utils import init_logger, logger
from common.board_graph import BoardGraph

from notification.feishu import FeiShu
from xt_data_db import TickDB 

strat_name = 'online'

from data_common import get_account_info, get_history_data

history_msgs = dict() # code, type, time

@cache_output(enable=True, force_update=False)
def init_board_graph():
    board_graph = BoardGraph()
    return board_graph

def split_tick_data_by_day(tick_data):
    dt = tick_data.iloc[0]['datetime'].date()
    end_dt = tick_data.iloc[-1]['datetime'].date()
    chunks = dict()
    ask_price_df = tick_data['askPrice'].apply(pd.Series)
    bid_price_df = tick_data['bidPrice'].apply(pd.Series)
    def calc_eval_price(row):
        if row['volume'] / 100 < 50:
            return np.nan
        if row['volume'] <= 0 or row['amount'] <= 0:
            return np.nan
        if np.isnan(row['volume']) or np.isnan(row['amount']):
            return np.nan
        return row['amount'] / row['volume']
    for i in range(5):
        tick_data[f'ask_price_{i}'] = ask_price_df[i].replace(0, np.nan)
        tick_data[f'bid_price_{i}'] = bid_price_df[i].replace(0, np.nan)
    while dt <= end_dt:
        one_chunk = tick_data.loc[dt.strftime("%Y-%m-%d")].copy()
        if len(one_chunk) > 0:
            one_chunk.loc[:, 'amount'] = one_chunk['acc_amount'].diff().fillna(0)
            one_chunk.loc[:, 'volume'] = one_chunk['acc_volume'].diff().fillna(0)
            one_chunk.loc[:, 'mid_price'] = (one_chunk['ask_price_0'] + one_chunk['bid_price_0']) / 2
            one_chunk.loc[:, 'eval_price'] = one_chunk.apply(calc_eval_price, axis=1)
            chunks[dt.strftime("%Y%m%d")] = one_chunk
        dt += datetime.timedelta(days=1) 
    return chunks

def calc_one_day_distribution(tick_data, price_ranges):
    res = pd.DataFrame()
    raw_data = list()
    for i in range(len(price_ranges) - 1):
        raw_data.append({'id': i, 'volume': 0, 'min_price': price_ranges[i], 'max_price': price_ranges[i+1]})
    res = pd.DataFrame(raw_data)
    res.set_index('id', inplace=True)
    for time, row in tick_data.iterrows():
        res.loc[(res['min_price'] <= row['price']) & (res['max_price'] > row['price']), 'volume'] += row['volume']
    return res

def calc_weights(day_size, decay):
    day_np = np.arange(0, day_size)
    day_exp_np = np.exp(-decay * day_np)
    day_exp_np = day_exp_np / np.sum(day_exp_np)
    return day_exp_np

def plot_clip_dist_info(info):
    from matplotlib import pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(1,6,6)
    d_price = info['d_price']
    ax.barh(info['total_dist']['min_price'], info['total_dist']['volume'], edgecolor='black', height=d_price)
    for i, clip_dist in enumerate(info['clip_dists']):
        sub_ax = fig.add_subplot(1, 6, i+1)
        sub_ax.barh(clip_dist['min_price'], clip_dist['volume'], edgecolor='black', height=d_price)
        for i, row in clip_dist.iterrows():
            pass
        sub_ax.set_title(f"{code}_{i}")
    plt.show()
   
def generate_feat(raw_data, enable_tick_data=False):
    day_data, min_data, tick_data = raw_data['day_data'], raw_data['min_data'], raw_data['tick_data']
    info = {'day_feat': dict(), 'min_feat': dict(), 'tick_feat': dict()}
    # day feat
    day_feat = info['day_feat']
    hist_5_day_data = day_data.iloc[-5:]
    last_day_data = day_data.iloc[-1]
    day_feat['max_5'] = hist_5_day_data['high'].max()
    day_feat['min_5'] = hist_5_day_data['low'].min()
    day_feat['mean_5'] = hist_5_day_data['close'].mean()
    day_feat['mean_volume_5'] = hist_5_day_data['volume'].mean()
    last_close = last_day_data['close']
    day_feat['day_neg_3'] = last_close * 0.97
    day_feat['day_neg_5'] = last_close * 0.95
    day_feat['day_neg_7'] = last_close * 0.93
    day_feat['day_neg_13'] = last_close * 0.87
    day_feat['day_pos_3'] = last_close  * 1.03
    day_feat['day_pos_5'] = last_close * 1.05
    day_feat['day_pos_7'] = last_close * 1.07
    day_feat['day_pos_13'] = last_close * 1.13

    # tick feat
    if enable_tick_data:
        tick_feat = info['tick_feat']
        day_size = 5
        tick_data_chunks = split_tick_data_by_day(tick_data)
        d_price = max(0.001, round((day_feat['max_5'] - day_feat['min_5']) / 50.0, 3))
        price_ranges = np.arange(day_feat['min_5'], day_feat['max_5'] + d_price, d_price)
        decay = 0.2
        weights = calc_weights(day_size, decay)
    
        tick_data_list = [(dt_str, chunk_data) for dt_str, chunk_data in tick_data_chunks.items()]
        tick_data_list = sorted(tick_data_list, key=lambda x: x[0], reverse=True)
        clip_distribution = None
        clip_dist_info = {'tick_datas': list(), 'clip_dists': list(), 'weights': list(), 'd_price': d_price}
        for i, (dt_str, chunk_data) in enumerate(tick_data_list):
            if i >= len(weights):
                break
            one_chunk_cd = calc_one_day_distribution(chunk_data, price_ranges)
            if clip_distribution is None:
                clip_distribution = one_chunk_cd.copy()
                clip_distribution['volume'] = weights[i] * clip_distribution['volume']
            else:
                clip_distribution['volume'] += weights[i] * one_chunk_cd['volume'].copy()
            #logger.info(f"{i}: {dt_str}")
            #logger.info(clip_distribution)
            clip_dist_info['tick_datas'].append(chunk_data)
            clip_dist_info['clip_dists'].append(one_chunk_cd)
            clip_dist_info['weights'].append(weights[i])
        clip_distribution['volume_pct'] = clip_distribution['volume'] / clip_distribution['volume'].sum()
        clip_dist_info['total_dist'] = clip_distribution
        volume_pct_threshold = 0.05
        tick_feat['large_volume_infos'] = clip_distribution[clip_distribution['volume_pct'] > volume_pct_threshold]
        tick_feat['max_volume_info'] = clip_distribution.nlargest(1, 'volume_pct')
        tick_feat['top_3_volume_info'] = clip_distribution.nlargest(3, 'volume_pct')
        logger.info(tick_feat)
        # plot_clip_dist_info(clip_dist_info)
    raw_data.update(info)

def check_cross_type(tick_data, val):
    latest_td = tick_data.iloc[-1]
    for i in range(len(tick_data)-2, -1, -1):
        td = tick_data.iloc[i]
        if latest_td['price'] >= val:
            if td['price'] < val:
                return 1
        elif latest_td['price'] <= val:
            if td['price'] > val:
                return -1
    return 0

def handle_one_code_one_bar(history_data, code, base_info, db, dt):
    time_range = [dt-datetime.timedelta(seconds=35), dt]
    tick_data = db.get_tick_data(code, time_range=time_range)  
    time_str = dt.strftime("%H:%M:%S")
    if len(tick_data) <= 3:
        if len(tick_data) <= 3:
            if "09:30:00" < time_str < "11:30:00" or "13:00:00" < time_str < "14:57:00":
                logger.error(f"tick data size is empty ({len(tick_data)}) @ {time_str}")
            return None, None
    tick_data['volume'] = tick_data['acc_volume'].diff(1)
    tick_data['amount'] = tick_data['acc_amount'].diff(1)
    # 验证最新tick
    last_tick = tick_data.iloc[-1]
    price = last_tick['price']
    if np.isnan(price) or last_tick['volume'] <= 0:
        return None, None
    day_feat, min_feat, tick_feat = history_data['day_feat'], history_data['min_feat'], history_data['tick_feat']
    last_day_close = history_data['day_data'].iloc[-1]['close']
    price_change_ratio = (price - last_day_close) / last_day_close * 100.0
    base_str = "{}({})@{} p({:.2f}/{:.1f}%):".format(code, base_info['name'], dt.strftime("%H:%M:%S"), price, price_change_ratio)
    info = {'code': code, 'name': base_info['name'], 'dt': dt, 'price': price, 'price_change_ratio': price_change_ratio}
    mv = base_info['total_mv'] / 1e8

    # tick_data信息计算
    sum_volume = tick_data['volume'].sum()
    sum_volume_ratio = 1.0 * sum_volume / day_feat['mean_volume_5'] * 100.0
    sum_amount = tick_data['amount'].sum()
    tick_price_range = [tick_data['price'].min(), tick_data['price'].max()]
    tick_start_price, tick_end_price = tick_data.iloc[0]['price'], tick_data.iloc[-1]['price']
    price_max_change_ratio = (tick_price_range[1] - tick_price_range[0]) / price * 100.0
    def update_history_msgs(code, tp, dt):
        global history_msgs
        if code in history_msgs:
            if tp in history_msgs[code]:
                last_dt = history_msgs[code][tp]
                if dt - last_dt < datetime.timedelta(seconds=120):
                    return False
                history_msgs[code][tp] = dt
            else:
                history_msgs[code][tp] = dt
        else:
            history_msgs[code] = {tp: dt}
        return True

    msg_dict = dict()
    if abs(price_max_change_ratio) > 2.0:
        tp = 'MAX_P_CR'
        if update_history_msgs(code, tp, dt):
            info_str = base_str + "[{}]({:.2f}%),amount({:.0f}w)".format(tp, price_max_change_ratio, sum_amount / 1e4)
            logger.info(info_str)
            msg_dict[tp] = {'price_max_change_ratio': price_max_change_ratio, 'sum_amount': sum_amount}
    if sum_volume_ratio > 5.0:
        tp = 'VOL_CR'
        if update_history_msgs(code, tp, dt):
            info_str = base_str + "[{}]({:.3f}%)".format(tp, sum_volume_ratio)
            logger.info(info_str)
            msg_dict[tp] = {'sum_volume_ratio': sum_volume_ratio}

    if abs(price_max_change_ratio) > 0:
        for k in ['max_5', 'min_5', 'day_neg_3', 'day_neg_7', 'day_neg_13', 'day_pos_3', 'day_pos_7', 'day_pos_13']:
            k_price = day_feat[k]
            if k_price < tick_price_range[0] or k_price > tick_price_range[1]:
                continue
            tp = None
            if tick_start_price != tick_end_price:
                if tick_start_price <= k_price <= tick_end_price:
                    tp = f'A_UP_{k}'
                elif tick_start_price >= k_price >= tick_end_price:
                    tp = f'A_DN_{k}'
            if tp is None:
                if tick_price_range[0] <= k_price <= tick_end_price:
                    tp = f'B_UP_{k}'
                elif tick_price_range[1] >= k_price >= tick_end_price:
                    tp = f'B_DN_{k}'
            if tp is None:
                continue
            if update_history_msgs(code, tp, dt):
                info_str = base_str + "[{}]p({:.2f})".format(tp, k_price)
                logger.info(info_str)
                msg_dict[tp] = {'k_price': k_price}
    msg_target_dict = {1: {}, 2: {}, 3: {}}
    for tp, msg_info in msg_dict.items():
        if mv > 1000.0:
            msg_target_dict[3][tp] = msg_info
        elif mv > 300:
            msg_target_dict[2][tp] = msg_info
        else:
            msg_target_dict[3][tp] = msg_info
    return msg_target_dict, info

def get_code_board_infos(code, board_graph, industry_board_infos, concept_board_infos):
    con_codes = board_graph.get_concepts_by_stock(code)
    ind_codes = board_graph.get_industrys_by_stock(code)
    infos = list()
    if con_codes is not None:
        for b_code, b_name, b_type in con_codes:
            if b_code not in concept_board_infos:
                continue
            board_info = concept_board_infos[b_code]
            b_score = board_info['w_scores'].iloc[-1]
            infos.append({'b_code': b_code, 'b_name': b_name, 'b_type': b_type, 'board_w_score': b_score})
    if ind_codes is not None:
        for b_code, b_name, b_type in ind_codes:
            if b_code not in industry_board_infos:
                continue
            board_info = industry_board_infos[b_code]
            b_score = board_info['w_scores'].iloc[-1]
            infos.append({'b_code': b_code, 'b_name': b_name, 'b_type': b_type, 'board_w_score': b_score})
    sorted_infos = sorted(infos, key=lambda x: x['board_w_score'], reverse=True)
    return sorted_infos

def get_one_code_history_data(board_graph, history_data_dir, code, cur_date, enable_tick_data=False, logger=None):
    data_path = history_data_dir / f"{code}.pkl"
    if data_path.exists():
        return load_data(data_path)
    from online.board.utils import load_intraday_data, load_one_day_data
    is_intraday = False
    if is_intraday:
        stock_data_dict, stock_sectional_data, industry_board_infos, concept_board_infos, index_board_infos, all_boards_sectional_infos = load_intraday_data()
    else:
        stock_data_dict, stock_sectional_data, industry_board_infos, concept_board_infos, index_board_infos, all_boards_sectional_infos = load_one_day_data()
    board_infos = get_code_board_infos(code, board_graph, industry_board_infos, concept_board_infos)
    from common.new_data_getter import download_data 
    end_date = datetime.datetime(cur_date.year, cur_date.month, cur_date.day, 0, 0, 0)
    start_date = end_date - datetime.timedelta(days=15)
    if logger:
        logger.info("Start update {} history_data data from ({}) to ({})".format(code, start_date, end_date))
    code_list = [code]
    download_data(code_list, start_date, end_date, period='1d', logger=logger)
    download_data(code_list, start_date, end_date, period='5m', logger=logger)
    download_data(code_list, start_date, end_date, period='tick', logger=logger)
    if logger:
        logger.info("Finish download data")
        logger.info("Start get data and generate feat")
    from common.new_data_getter import DataGetter
    data_getter = DataGetter()
    day_data_dict = data_getter.get_data(code_list, start_datetime=start_date, end_datetime=end_date, period='1d')
    min_data_dict = data_getter.get_data(code_list, start_datetime=start_date, end_datetime=end_date, period='5m')
    tick_data_dict = list()
    if enable_tick_data:
        tick_data_dict = data_getter.get_data(code_list, start_datetime=start_date, end_datetime=end_date, period='tick')
    data = {'day_data': day_data_dict, 'min_data': min_data_dict, 'tick_data': tick_data_dict, 'board_infos': board_infos}
    generate_feat(data, enable_tick_data)
    with open(data_path, 'wb') as f:
        pickle.dump(data, f)
    if logger:
        logger.info("Get data day data size({}), min data size({}), tick data size({}), and save to {}".format(
            len(data['day_data']), len(data['min_data']), len(data['tick_data']), data_path))
    return data
    
def handle_one_bar(board_graph, history_data_dir, history_data_dict, cur_date, db, codes_dict, now_dt, enable_tick_data=False, feishu=None):
    logger.info(f"Handle {len(codes)} codes @ {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    code_msg_dict = dict()
    for code, base_info in codes_dict.items():
        if code not in history_data_dict:
            history_data_dict[code] = get_one_code_history_data(board_graph, history_data_dir, code, cur_date, enable_tick_data)
        history_data = history_data_dict[code]
        msg_target_dict, info = handle_one_code_one_bar(history_data, code, base_info, db, now_dt)
        if msg_target_dict is None or len(msg_target_dict) <= 0:
            continue
        code_msg_dict[code] = (msg_target_dict, info)
    feishu_output(now_dt, code_msg_dict, codes_dict, history_data_dict)

def feishu_output(now_dt, code_msg_dict, codes_dict, history_data_dict):
    if len(code_msg_dict) <= 0:
        return
    base_str = "@{}:".format(now_dt.strftime("%H:%M:%S"))
    feishu_strs = dict()
    for target in [1, 2, 3]:
        info_str = ""
        for code, (msg_target_dict, info) in code_msg_dict.items():
            if target not in msg_target_dict or len(msg_target_dict[target]) <= 0:
                continue
            info_str += "\n\n"
            mv = codes_dict[code]['total_mv'] / 1e8
            board_infos = history_data_dict[code]['board_infos']
            board_infos_str = ""
            for bi in board_infos[0:3]:
                board_infos_str += "({}/{:.0f})".format(bi['b_name'], bi['board_w_score'])
            info_str += "Code({},{},{:.0f}),{}\n  p({:.2f}/{:.1f}%):".format(info['code'], info['name'], mv, board_infos_str,
                                                                      info['price'], info['price_change_ratio'])
            for tp, detail in msg_target_dict[target].items():
                info_str += f"[{tp}]"
        if len(info_str) <= 0:
            continue
        # print(target, base_str + info_str)
        if feishu is not None:
            feishu.send_user_message(base_str + info_str, target=target)

def update_history(history_data_dir, codes_dict, cur_date, enable_tick_data=False):
    logger.info(f"Update history data for {len(codes)} codes @ cur date {cur_date}")
    for code, base_info in tqdm(codes_dict.items()):
        res = get_one_code_history_data(board_graph, history_data_dir, code, cur_date, enable_tick_data)
    
if __name__ == "__main__":
    init_logger(strat_name, "/tmp/{}".format("online"))
    parser = argparse.ArgumentParser(description='position_analysis')
    parser.add_argument('--reset', action='store_true', help='reset')
    parser.add_argument('--debug', action='store_true', help='debug')
    parser.add_argument('--enable_tick_data', action='store_true', help='debug')
    args = parser.parse_args()
    
    feishu = FeiShu()
    board_graph = init_board_graph()

    cur_date = datetime.datetime.now()
    if args.debug:
        cur_date = datetime.datetime(2025, 9, 30)
    cur_date_str = cur_date.strftime("%Y%m%d")

    # init history_data
    history_data_dir = Path(f"/tmp/cache_output/online/history_data/{cur_date_str}")
    history_data_dir.mkdir(parents=True, exist_ok=True)
    history_data_dict = dict()
    
    db_data_dir = Path("/tmp") / "cache_output" / "xt_data_db"
    db_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_data_dir / f"tick_data_{cur_date.strftime('%Y%m%d')}.db"
    if not db_path.exists():
        logger.error(f"{db_path} database is not existed!")
        exit()
    db = TickDB(db_path, [])

    from xt_data_db import load_candidates
    can_codes_1, can_codes_2 = load_candidates()
    codes = can_codes_2
    data_dir = Path("/tmp/cache_output/date_info/")
    data_path = data_dir / "stock_base_infos.pkl"
    stock_base_infos = load_data(data_path)
    codes_dict = dict()
    for code in codes:
        codes_dict[code] = stock_base_infos[code]
    logger.info(f"Candidates size({len(codes)})")

    update_history(history_data_dir, codes_dict, cur_date, enable_tick_data=args.enable_tick_data)

    if args.debug:
        feishu = None
        for i in range(30):
            now = datetime.datetime(cur_date.year, cur_date.month, cur_date.day, 9, 24, 50) + datetime.timedelta(seconds=i*5)
            logger.info(f"Handle @{now}")
            handle_one_bar(board_graph, history_data_dir, history_data_dict, cur_date, db, codes_dict, now, enable_tick_data=args.enable_tick_data, feishu=feishu)
        exit()

    logger.info("Start monitor")
    while True:
        now = datetime.datetime.now()
        if now.time() <= datetime.time(9, 24, 40):
            continue
        logger.info(f"Handle @{now}")
        handle_one_bar(board_graph, history_data_dir, history_data_dict, cur_date, db, codes_dict, now, enable_tick_data=args.enable_tick_data, feishu=feishu)
        if now.time() >= datetime.time(15, 0, 3):
            break
        time.sleep(30)
