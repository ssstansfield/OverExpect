import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm_notebook, tnrange
import sqlalchemy
engine = sqlalchemy.create_engine('mysql://root:Ss888888@127.0.0.1:3306/gds')
from xtquant import xtdatacenter as xtdc
xtdc.set_token('545fbf3493e048987056052b2d1988e5574fab15')
xtdc.set_data_home_dir('D:/XTdata') 
xtdc.init()
# 导入 xtdata
from xtquant import xtdata  
import rqdatac as rq
rq.init('15805988503', 'Ss888888')
from utils import *
import json

# ==================================基础数据==================================
stockList = xtdata.get_stock_list_in_sector('沪深A股')
count = -1
price_data = xtdata.get_market_data_ex([],stockList, period='1d', start_time='20190101', end_time='', dividend_type='back_ratio')
reports_dict = xtdata.get_financial_data(stockList, table_list=['Income'], start_time='20190101', end_time='', report_type='report_time')
reports = pd.DataFrame()
for stock in tqdm_notebook(reports_dict.keys()):
    report_stk = reports_dict[stock]['Income']
    report_stk['stock_code'] = [stock] * len(report_stk)
    reports = pd.concat([reports, report_stk])

sql_forecast = '''
        SELECT id, stock_code, stock_name, declare_date FROM gds.fin_performance_forecast
        ORDER BY declare_date
'''
forecast_all = pd.read_sql(sql_forecast, engine) # 所有业绩预告数据，不过滤类型，仅作为信息时间
forecast_all.drop_duplicates('id', inplace=True)
forecast_all.reset_index(drop=True, inplace=True)

sql_express = '''
        SELECT id, stock_code, stock_name, declare_date FROM gds.fin_performance_express
        ORDER BY declare_date
'''
express_all = pd.read_sql(sql_express, engine) # 所有业绩快报数据，不过滤类型，仅作为信息时间
express_all.drop_duplicates('id', inplace=True)
express_all.reset_index(drop=True, inplace=True)

sql_adj = '''
        SELECT id, stock_code, stock_name, title, current_create_date, np_adjust_mark FROM gds.rpt_earnings_adjust
        ORDER BY current_create_date
'''
adj_all = pd.read_sql(sql_adj, engine) # 所有盈利预测数据，不过滤类型
adj_all.drop_duplicates('id', inplace=True)
adj_all.reset_index(drop=True, inplace=True)
adj_all.fillna(4, inplace=True)

sql_rpt_forecast_stk = '''
    SELECT id, stock_code, stock_name, title
    FROM rpt_forecast_stk
'''
rpt_forecast_stk = pd.read_sql(sql_rpt_forecast_stk, engine)
rpt_forecast_stk.drop_duplicates('id', inplace=True)

title_overExpect = pd.concat([adj_all[adj_all['title'].str.contains('超预期')], rpt_forecast_stk[rpt_forecast_stk['title'].str.contains('超预期')]])
title_overExpect.drop_duplicates('id', inplace=True)
title_overExpect.reset_index(drop=True, inplace=True)

# ==================================数据处理==================================
# 统一日期格式
tradeDates = xtdata.get_trading_calendar(market='SH', start_time='20190101', end_time='20300101')
# 基础数据price_data 以str为index
# 业绩预告和业绩快报以yyyy-mm-dd为declare_date, 改为yyyymmdd
forecast_all['declare_date'] = pd.to_datetime(forecast_all['declare_date']).dt.strftime('%Y%m%d')
express_all['declare_date'] = pd.to_datetime(express_all['declare_date']).dt.strftime('%Y%m%d')
# 财报数据的m_anntime列为yyyymmdd
# 调升数据的current_create_date列为yyyy-mm-dd
adj_all['current_create_date'] = pd.to_datetime(adj_all['current_create_date']).dt.strftime('%Y%m%d')
# 标题超预期数据的current_create_date列为yyyy-mm-dd
title_overExpect['current_create_date'] = pd.to_datetime(title_overExpect['current_create_date']).dt.strftime('%Y%m%d')

# 交易代码格式

# 业绩预告和业绩快报stock_code转换
stk_code_normal = []
for stk_code in tqdm_notebook(forecast_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rq.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
forecast_all['stock_code_normal'] = stk_code_normal
forecast_all.dropna(subset=['stock_code_normal'], inplace=True)
forecast_all.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm_notebook(express_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rq.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
express_all['stock_code_normal'] = stk_code_normal
express_all.dropna(subset=['stock_code_normal'], inplace=True)
express_all.reset_index(drop=True, inplace=True)

# 分析师调升和标题超预期stock_code转换
stk_code_normal = []
for stk_code in tqdm_notebook(adj_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rq.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
adj_all['stock_code_normal'] = stk_code_normal
adj_all.dropna(subset=['stock_code_normal'], inplace=True)
adj_all.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm_notebook(title_overExpect['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rq.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
title_overExpect['stock_code_normal'] = stk_code_normal
title_overExpect.dropna(subset=['stock_code_normal'], inplace=True)
title_overExpect.reset_index(drop=True, inplace=True)

def is_st(stock:str, date:str):
    """
    stock: 'xxxxxx.SH', date: 'yyyymmdd'
    """
    stock_dict = xtdata.get_his_st_data(stock)
    for st_period in stock_dict.get('ST', []):
        start_date, end_date = st_period
        if start_date <= date <= end_date:
            return True
    for st_period in stock_dict.get('*ST', []):
        start_date, end_date = st_period
        if start_date <= date <= end_date:
            return True
    for st_period in stock_dict.get('PT', []):
        start_date, end_date = st_period
        if start_date <= date <= end_date:
            return True
    return False

# ==================================策略==================================
portfolio_dict = {}
start_date = '20190107'
end_date = '20240521'
tradeDates = xtdata.get_trading_calendar(market='SH', start_time='20190101', end_time='20300101')
tradeDates = [date for date in tradeDates if date >= '20190101' and date <= end_date]

for idx in tnrange(len(tradeDates)):
    test_end = tradeDates[idx]
    test_date = tradeDates[idx - 5]
    # 区间披露财报
    period_reports = reports[reports['m_anntime'] == test_date]
    if period_reports.empty:
        continue
    valid_candidates = []
    for row in range(period_reports.shape[0]):
        code = period_reports.iloc[row]['stock_code']
        info_date = period_reports.iloc[row]['m_anntime'] #披露日期
        if (all_raise(code, info_date, adj_all, days=5, num_experts=5) or overExpect_in_title(code, info_date, title_overExpect, days=5)) and not is_st(code, test_end):
            valid_candidates.append(code)
    portfolio_dict[test_end] = valid_candidates


# 加入业绩预告数据
for idx in tnrange(len(tradeDates)):
    test_end = tradeDates[idx]
    test_date = tradeDates[idx - 5]
    # 区间业绩预告
    period_forecast = forecast_all[forecast_all['declare_date'] == test_date]
    if period_forecast.empty:
        continue
    try:
        valid_candidates = portfolio_dict[test_end]
    except KeyError:
        valid_candidates = []
    for row in range(period_forecast.shape[0]):
        code = period_forecast.iloc[row]['stock_code_normal']
        info_date = period_forecast.iloc[row]['declare_date'] #披露日期
        if (all_raise(code, info_date, adj_all, days=5, num_experts=5) or overExpect_in_title(code, info_date, title_overExpect, days=5)) and not is_st(code, test_end):
            valid_candidates.append(code)
    portfolio_dict[test_end] = valid_candidates

# 加入业绩快报数据
for idx in tnrange(len(tradeDates)):
    test_end = tradeDates[idx]
    test_date = tradeDates[idx - 5]
    # 区间业绩快报
    period_express = express_all[express_all['declare_date'] == test_date]
    if period_express.empty:
        continue
    try:
        valid_candidates = portfolio_dict[test_end]
    except KeyError:
        valid_candidates = []
    for row in range(period_express.shape[0]):
        code = period_express.iloc[row]['stock_code_normal']
        info_date = period_express.iloc[row]['declare_date'] #披露日期
        if (all_raise(code, info_date, adj_all, days=5, num_experts=5) or overExpect_in_title(code, info_date, title_overExpect, days=5)) and not is_st(code, test_end):
            valid_candidates.append(code)
    portfolio_dict[test_end] = valid_candidates


with open('portfolio_gds_daily.json', 'w') as f:
    json.dump(portfolio_dict, f)