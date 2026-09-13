import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm, tnrange
import sqlalchemy
engine = sqlalchemy.create_engine('mysql://root:Ss888888@127.0.0.1:3306/gds')
import rqdatac
rqdatac.init('15805988503', 'Ss888888')

def SUE(stock_code, date: str, num_monitoring: int, reports_dict: dict):
    try:
        reports = reports_dict[stock_code]['Income']
    except KeyError:
        print(f"{stock_code} on {date} not found in reports_dict")
        return np.nan

    # 过滤掉日期晚于指定日期的数据，并去重
    reports = reports[reports['m_anntime'] <= date].drop_duplicates('m_timetag', keep='last')

    if reports.shape[0] < num_monitoring + 5:
        return np.nan

    reports.set_index('m_timetag', inplace=True)
    time_tags = reports.index
    current_timetag = time_tags[-1]

    # 获取当前和之前的净利润
    current_np = reports.loc[current_timetag, 'net_profit_incl_min_int_inc']
    last_np = reports.iloc[-5]['net_profit_incl_min_int_inc']
    past_np_delta = reports['net_profit_incl_min_int_inc'].diff(4).iloc[-(num_monitoring+1):-1].values

    expected_np = last_np + past_np_delta.mean()
    SUE = (current_np - expected_np) / past_np_delta.std()

    return SUE

def DeltaROEQ(stock_code:str, date:str, PershareIndex_dict:dict):
    try:
        stk_indexes = PershareIndex_dict[stock_code]['PershareIndex']
    except KeyError:
        print(stock_code, date, 'not in PershareIndex_dict')
        return np.nan
    stk_indexes = stk_indexes[stk_indexes['m_anntime'] <= date]
    stk_indexes.drop_duplicates('m_timetag', keep='last', inplace=True)
    stk_indexes.set_index('m_timetag', inplace=True)
    current_timetag = stk_indexes.index[-1]
    # 删去当前时间点之后的数据
    stk_indexes = stk_indexes.loc[:current_timetag]
    # 判断数据是否足够
    if stk_indexes.shape[0] < 5:
        return np.nan
    current_ROE = stk_indexes.loc[current_timetag]['net_roe']
    last_ROE = stk_indexes.iloc[-5]['net_roe']
    DeltaROEQ = current_ROE - last_ROE
    return DeltaROEQ

def NPAdjustRate(stk_code_normal:str, date:str, adj_all:pd.DataFrame):
    date = pd.to_datetime(date, format='%Y%m%d')
    start = date - pd.Timedelta(days=90)
    period_adj = adj_all[(adj_all['stk_code_normal'] == stk_code_normal) & (adj_all['entrytime'] >= start) & (adj_all['entrytime'] <= date)]
    if period_adj.empty:
        return 0
    else:
        return period_adj['np_adjust_rate'].median()
    
def find_nearest_trading_date(trading_dates, target_date, latter=False):
    # 将目标日期转换为Timestamp对象
    target_date = pd.to_datetime(target_date, format='%Y%m%d')

    # 遍历交易日期列表，找到最接近的日期
    nearest_date = min(trading_dates, key=lambda date: abs(date - target_date))
    if latter:
        if nearest_date <= target_date:
            nearest_date = trading_dates[trading_dates.get_loc(nearest_date) + 1]
    return nearest_date.strftime('%Y%m%d'), trading_dates.get_loc(nearest_date)

def AOG(stock_code:str, date:str, reports:pd.DataFrame, forecast_all:pd.DataFrame, express_all:pd.DataFrame, price_data:dict, zz500:pd.DataFrame, tradeDates:pd.Series, tradeDates_ts:pd.Series):
    date = pd.to_datetime(date, format='%Y%m%d')
    date_str = date.strftime('%Y%m%d')
    latest_report = reports[(reports['stock_code'] == stock_code) & (reports['m_anntime'] <= date_str)]
    if not latest_report.empty:
        latest_report_date_str = latest_report.iloc[-1]['m_anntime']
    else:
        latest_report_date_str = '20090101'
    latest_forecast = forecast_all[(forecast_all['stk_code_normal'] == stock_code) & (forecast_all['declare_date'] <= date_str)]
    if not latest_forecast.empty:
        latest_forecast_date = latest_forecast.iloc[-1]['declare_date']
    else:
        latest_forecast_date = '20090101'
    latest_express = express_all[(express_all['stk_code_normal'] == stock_code) & (express_all['declare_date'] <= date_str)]
    if not latest_express.empty:
        latest_express_date = latest_express.iloc[-1]['declare_date']
    else:
        latest_express_date = '20090101'

    latest_date_str = max(latest_report_date_str, latest_forecast_date, latest_express_date)
    if latest_date_str == '20090101':
        return 0
    
    if latest_date_str in tradeDates:
        next_date = tradeDates[tradeDates.index(latest_date_str) + 1]
    else:
        latest_date_str, idx = find_nearest_trading_date(tradeDates_ts, latest_date_str, latter=True)
        next_date = tradeDates[tradeDates.index(latest_date_str) + 1]
    try:
        Open_stk_next = price_data[stock_code].loc[next_date]['open']
        Close_stk_latest = price_data[stock_code].loc[latest_date_str]['close']
    except KeyError:
        print(stock_code, date, next_date, latest_date_str)
        return 0
    zz500_next = zz500.loc[next_date]['open']
    zz500_t_latest = zz500.loc[latest_date_str]['close']
    AOG = (Open_stk_next/Close_stk_latest) - (zz500_next/zz500_t_latest)
    return AOG

def HIGH250(stock_code:str, date:str, reports:pd.DataFrame, forecast_all:pd.DataFrame, express_all:pd.DataFrame, price_data:dict, zz500:pd.DataFrame, tradeDates:pd.Series, tradeDates_ts:pd.Series):
    date = pd.to_datetime(date, format='%Y%m%d')
    date_str = date.strftime('%Y%m%d')
    latest_report = reports[(reports['stock_code'] == stock_code) & (reports['m_anntime'] <= date_str)]
    if not latest_report.empty:
        latest_report_date_str = latest_report.iloc[-1]['m_anntime']
    else:
        latest_report_date_str = '20090101'
    latest_forecast = forecast_all[(forecast_all['stk_code_normal'] == stock_code) & (forecast_all['declare_date'] <= date_str)]
    if not latest_forecast.empty:
        latest_forecast_date = latest_forecast.iloc[-1]['declare_date']
    else:
        latest_forecast_date = '20090101'
    latest_express = express_all[(express_all['stk_code_normal'] == stock_code) & (express_all['declare_date'] <= date_str)]
    if not latest_express.empty:
        latest_express_date = latest_express.iloc[-1]['declare_date']
    else:
        latest_express_date = '20090101'

    latest_date = max(latest_report_date_str, latest_forecast_date, latest_express_date)
    if latest_date == '20090101':
        return 0
    
    if latest_date in tradeDates:
        next_date = tradeDates[tradeDates.index(latest_date) + 1]
    else:
        latest_date, idx = find_nearest_trading_date(tradeDates_ts, latest_date, latter=True)
        next_date = tradeDates[tradeDates.index(latest_date) + 1]
    try:
        Close_stk_next = price_data[stock_code].loc[next_date]['close']
    except KeyError:
        print(stock_code, date, next_date)
        return 0

    start_date_str = tradeDates[tradeDates.index(latest_date) - 250]
    try:
        period_max_price = max(price_data[stock_code].loc[start_date_str:latest_date]['close'])
    except:
        print(stock_code, date, start_date_str, latest_date)
        return 0
    HIGH250 = (Close_stk_next - period_max_price) / period_max_price
    return HIGH250

def totalMV(stk_code:str, date:str, price_data:dict, capital_dict:dict):
    try:
        capital_df = capital_dict[stk_code]['Capital']
    except KeyError:
        print(stk_code, date, 'not in capital_dict')
        return 0
    capital_df = capital_df[capital_df['m_anntime'] <= date]
    if capital_df.empty:
        return 0
    capital = capital_df.iloc[-1]['total_capital']
    price = price_data[stk_code].loc[date]['close']
    return capital * price

def get_ranking(inputList, ascending):
    inputList = list(inputList)
    if ascending:
        sorted_list_with_indices = sorted(enumerate(inputList), key=lambda x: x[1])
    else:
        sorted_list_with_indices = sorted(enumerate(inputList), key=lambda x: x[1], reverse=True)

    rank_list = [0] * len(inputList)
    current_rank = 0
    for index, _ in sorted_list_with_indices:
        rank_list[index] = current_rank
        current_rank += 1

    return rank_list



def convert_period(report_year, report_period, source:str) -> str:
    report_year = str(report_year)
    report_period = str(report_period)
    if source == 'forecast':
        if report_period == '1':
            return report_year + '0331'
        elif report_period == '2':
            return report_year + '0630'
        elif report_period == '3':
            return report_year + '0930'
        elif report_period == '4':
            return report_year + '1231'
        else:
            return np.nan
    elif source == 'appo_rele':
        if report_period == '1001':
            return report_year + '0331'
        elif report_period == '1002':
            return report_year + '0630'
        elif report_period == '1003':
            return report_year + '0930'
        elif report_period == '1004':
            return report_year + '1231'
        else:
            return np.nan

# info_date后days天内是否有超预期标题
def overExpect_in_title(stk_code, info_date, title_overExpect:pd.DataFrame, days=5):
    title_overExpect = title_overExpect[title_overExpect['stock_code_normal'] == stk_code]
    title_overExpect = title_overExpect[title_overExpect['current_create_date'] >= info_date]
    title_overExpect = title_overExpect[title_overExpect['current_create_date'] <= (pd.to_datetime(info_date) + pd.Timedelta(days=days)).strftime('%Y%m%d')]
    if title_overExpect.empty:
        return False
    return True

# stk_code 在 info_date 披露后5天内至少有5个以上分析师覆盖并全部调升
# 盈利调整数据
# 1 未调，2 调高，3 调低，4 未知
def get_label_vals(label_vals):
    try:
        num_up = label_vals[2]
    except KeyError:
        num_up = 0
    try:
        num_down = label_vals[3]
    except KeyError:
        num_down = 0
    try:
        num_keep = label_vals[1]
    except KeyError:
        num_keep = 0
    try:
        num_null = label_vals[4]
    except KeyError:
        num_null = 0
    return num_up, num_down, num_keep, num_null

# 判断是否符合5个调升0调平0调低的条件
def all_raise(stk_code, report_date, np_adj:pd.DataFrame, days=5, num_experts=5):
    test = np_adj[np_adj['stock_code_normal'] == stk_code]
    test_start = pd.to_datetime(report_date)
    test_end = test_start + pd.Timedelta(days=days)

    # 日期转换为str
    test_start = test_start.strftime('%Y%m%d')
    test_end = test_end.strftime('%Y%m%d')

    test_period = test[(test['current_create_date'] >= test_start) & (test['current_create_date'] <= test_end)]
    if test_period.empty:
        return False
    label_vals = test_period.value_counts('np_adjust_mark')
    num_up, num_down, num_keep, num_null = get_label_vals(label_vals)
    if num_up >= num_experts and num_down == 0 and num_keep == 0:
        return True
    else:
        return False

# 业绩大增
def big_increase(stk_code, date:str, reports_dict:dict):
    try:
        reports = reports_dict[stk_code]['Income']
    except KeyError:
        print(stk_code, date, 'not in reports_dict')
        return False
    reports = reports[reports['m_anntime'] <= date]
    if reports.empty:
        return False
    reports.set_index('m_timetag', inplace=True)
    current_timetag = reports.index[-1]
    if reports.shape[0] < 5:
        return False
    current_np = reports.loc[current_timetag]['net_profit_excl_min_int_inc']
    last_np = reports.iloc[-5]['net_profit_excl_min_int_inc']
    if current_np > 10000000 and (current_np - last_np) / last_np > 0.5 and last_np >= 0:
        return True
    else:
        return False

def big_increase_forecast(stk_code, date:str, period_forecast_stock:pd.DataFrame, reports_dict:dict):
    try:
        reports = reports_dict[stk_code]['Income']
    except KeyError:
        print(stk_code, date, 'not in reports_dict')
        return False
    reports = reports[reports['m_anntime'] <= date]
    if reports.empty:
        return False
    reports.set_index('m_timetag', inplace=True)
    if reports.shape[0] < 5:
        return False
    forecast_year = period_forecast_stock['report_year']
    forecast_period = period_forecast_stock['report_period']
    time_tag = convert_period(forecast_year, forecast_period, 'forecast')
    reports = reports[:time_tag]
    last_np = reports.iloc[-5]['net_profit_excl_min_int_inc']
    current_np_forecast = 10000*(period_forecast_stock['np_floor'])
    if current_np_forecast > 10000000 and (current_np_forecast - last_np) / last_np > 0.5 and last_np >= 0:
        return True
    else:
        return False