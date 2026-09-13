import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm_notebook, tnrange

def find_nearest_trading_date(trading_dates, target_date, latter=False):
    # 将目标日期转换为Timestamp对象
    target_date = pd.to_datetime(target_date, format='%Y%m%d')

    # 遍历交易日期列表，找到最接近的日期
    nearest_date = min(trading_dates, key=lambda date: abs(date - target_date))
    if latter:
        if nearest_date <= target_date:
            nearest_date = trading_dates[trading_dates.get_loc(nearest_date) + 1]
    return nearest_date.strftime('%Y%m%d'), trading_dates.get_loc(nearest_date)

def calculate_max_drawdown(net_values):
    net_values = np.array(net_values)
    peak_values = np.maximum.accumulate(net_values)
    drawdowns = (peak_values - net_values) / peak_values
    max_drawdown = np.max(drawdowns)
    return max_drawdown

def calculate_returns(net_values:list):
    init_value = net_values[0]
    daily_returns = [(value - init_value) / init_value for value in net_values]
    return daily_returns

def calculate_tracking_error(fund_value, benchmark_value):
    fund_value = np.array(fund_value)
    benchmark_value = np.array(benchmark_value)
    fund_pct_change = fund_value[1:] / fund_value[:-1] - 1
    benchmark_pct_change = benchmark_value[1:] / benchmark_value[:-1] - 1
    tracking_error = np.std(fund_pct_change - benchmark_pct_change, ddof=1)
    return tracking_error

def calculate_information_ratio(fund_value, benchmark_value, tracking_error=None):
    fund_returns = np.array(calculate_returns(fund_value))
    benchmark_returns = np.array(calculate_returns(benchmark_value))
    excess_returns = fund_returns - benchmark_returns
    mean_excess_return = np.mean(excess_returns)
    if tracking_error is None:
        tracking_error = calculate_tracking_error(fund_value, benchmark_value)
    information_ratio = mean_excess_return / tracking_error
    return information_ratio