import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm, tnrange
import sqlalchemy
import json
engine = sqlalchemy.create_engine('mysql://root:Ss888888@127.0.0.1:3306/gds')
import warnings
warnings.filterwarnings('ignore')
import rqdatac
rqdatac.init('15805988503', 'Ss888888')
from xtquant import xtdatacenter as xtdc
xtdc.set_token('545fbf3493e048987056052b2d1988e5574fab15')
xtdc.set_data_home_dir('D:/XTdata') 
xtdc.init()
from xtquant import xtdata
from utils import *

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

# ==========================================================================================================================================
# 基础数据
stockList = xtdata.get_stock_list_in_sector('沪深A股')
count = -1
price_data = xtdata.get_market_data_ex([],stockList, period='1d', start_time='20190101', end_time='', dividend_type='back')
tradeDates = xtdata.get_trading_calendar(market='SH', start_time='20170101', end_time='20300101')
tradeDates_ts = pd.to_datetime(tradeDates)
zz500 = xtdata.get_market_data_ex([],['000905.SH'], period='1d', start_time='20190101', end_time='')['000905.SH']
zz500.reset_index(inplace=True)
zz500.rename(columns={'index':'Date'}, inplace=True)
zz500.set_index('Date', inplace=True)

# 业绩预告和业绩快报
sql_forecast = '''
        SELECT id, stock_code, stock_name, declare_date, report_year, report_period, np_floor, np_rate_floor
        FROM gds.fin_performance_forecast
        WHERE is_valid = 1
        ORDER BY declare_date
'''
forecast_all = pd.read_sql(sql_forecast, engine) # 所有业绩预告数据，不过滤类型，仅作为信息时间
forecast_all.drop_duplicates('id', inplace=True)
forecast_all.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm(forecast_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
forecast_all['stk_code_normal'] = stk_code_normal

sql_express = '''
        SELECT id, stock_code, stock_name, declare_date 
        FROM gds.fin_performance_express
        ORDER BY declare_date
'''
express_all = pd.read_sql(sql_express, engine) # 所有业绩快报数据，不过滤类型，仅作为信息时间
express_all.drop_duplicates('id', inplace=True)
express_all.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm(express_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
express_all['stk_code_normal'] = stk_code_normal

# 财报
reports_dict = xtdata.get_financial_data(stockList, table_list=['Income'], start_time='20090101', end_time='', report_type='report_time')
PershareIndex_dict = xtdata.get_financial_data(stockList, table_list=['PershareIndex'], start_time='20090101', end_time='', report_type='report_time')
reports = pd.DataFrame()
for stock in tqdm(reports_dict.keys()):
    report_stk = reports_dict[stock]['Income']
    report_stk['stock_code'] = [stock] * len(report_stk)
    reports = pd.concat([reports, report_stk])
capital_dict = xtdata.get_financial_data(stockList, table_list=['Capital'], start_time='20090101', end_time='', report_type='report_time')

# 分析师净利润预测调整数据
sql_adj = '''
        SELECT id, stock_code, stock_name, title, current_create_date, report_year, np_adjust_mark, np_adjust_rate, entrytime 
        FROM gds.rpt_earnings_adjust
        WHERE is_valid = 1
        ORDER BY current_create_date
'''
adj_all = pd.read_sql(sql_adj, engine) # 所有盈利预期调整数据，不过滤类型
adj_all.drop_duplicates('id', inplace=True)
adj_all.reset_index(drop=True, inplace=True)
adj_all.fillna(4, inplace=True)

stk_code_normal = []
for stk_code in tqdm(adj_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
adj_all['stk_code_normal'] = stk_code_normal

# 研报标题超预期
# adj_all 的title列含有“超预期”的数据
sql_rpt_forecast_stk = '''
    SELECT id, stock_code, stock_name, title, entrytime
    FROM rpt_forecast_stk
'''
rpt_forecast_stk = pd.read_sql(sql_rpt_forecast_stk, engine)
rpt_forecast_stk.drop_duplicates('id', inplace=True)

title_overExpect = pd.concat([adj_all[adj_all['title'].str.contains('超预期')], rpt_forecast_stk[rpt_forecast_stk['title'].str.contains('超预期')]])
title_overExpect.drop_duplicates('id', inplace=True)
title_overExpect.reset_index(drop=True, inplace=True)

# 预约披露日期
sql_fin_appo_rele_date = '''
    SELECT id, stock_code, stock_name, report_year, report_quarter, declare_date, appo_rele_date
    FROM fin_appo_rele_date
    WHERE is_valid = 1
'''
appo_rele_date = pd.read_sql(sql_fin_appo_rele_date, engine)
appo_rele_date.drop_duplicates('id', inplace=True)
appo_rele_date.reset_index(drop=True, inplace=True)

# ==========================================================================================================================================
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
appo_rele_date['declare_date'] = pd.to_datetime(appo_rele_date['declare_date']).dt.strftime('%Y%m%d')

# 统一交易代码格式
# 业绩预告和业绩快报stock_code转换
stk_code_normal = []
for stk_code in tqdm(forecast_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
forecast_all['stock_code_normal'] = stk_code_normal
forecast_all.dropna(subset=['stock_code_normal'], inplace=True)
forecast_all.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm(express_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
express_all['stock_code_normal'] = stk_code_normal
express_all.dropna(subset=['stock_code_normal'], inplace=True)
express_all.reset_index(drop=True, inplace=True)

# 分析师调升和标题超预期stock_code转换
stk_code_normal = []
for stk_code in tqdm(adj_all['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
adj_all['stock_code_normal'] = stk_code_normal
adj_all.dropna(subset=['stock_code_normal'], inplace=True)
adj_all.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm(title_overExpect['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
title_overExpect['stock_code_normal'] = stk_code_normal
title_overExpect.dropna(subset=['stock_code_normal'], inplace=True)
title_overExpect.reset_index(drop=True, inplace=True)

stk_code_normal = []
for stk_code in tqdm(appo_rele_date['stock_code'].tolist()):
    try: 
        stk_code_normal.append(rqdatac.id_convert(stk_code, to='normal'))
    except:
        stk_code_normal.append(np.nan)
appo_rele_date['stock_code_normal'] = stk_code_normal
appo_rele_date.dropna(subset=['stock_code_normal'], inplace=True)
appo_rele_date.reset_index(drop=True, inplace=True)
# ==========================================================================================================================================


class track():
    def __init__(self, appo_rele_date:pd.DataFrame, reports:pd.DataFrame, reports_dict:dict, forecast_all:pd.DataFrame, express_all:pd.DataFrame, adj_all:pd.DataFrame, title_overExpect:pd.DataFrame, price_data:dict, zz500:pd.DataFrame, tradeDates:pd.Series, tradeDates_ts:pd.Series, capital_dict:dict, PershareIndex_dict:dict):
        '''
        trackingDict = {stock_code: x_days_to_report, nan stands for unknown}
        x>20 or nan or x<0: 未公布和已发财报 第3档
        10<x<=20: 第二档
        0<x<=10: 第一档
        '''
        self.trackingDict = {}
        self.trackingDict_entry = {}
        self.appo_rele_date = appo_rele_date
        self.reports = reports
        self.reports_dict = reports_dict
        self.forecast_all = forecast_all
        self.express_all = express_all
        self.adj_all = adj_all
        self.title_overExpect = title_overExpect
        self.price_data = price_data
        self.zz500 = zz500
        self.tradeDates = tradeDates
        self.tradeDates_ts = tradeDates_ts
        self.capital_dict = capital_dict
        self.PershareIndex_dict = PershareIndex_dict

    def update_trackingDict(self, date_str:str, days:int):
        '''
        date_str: 'yyyymmdd'
        stock_code: 'xxxxxx.SH'
        days: int, 观察天数
        '''
        date = pd.to_datetime(date_str, format='%Y%m%d')
        # date前5天内是否有超预期标题或业绩大增或分析师全部调升
        test_end_idx = tradeDates.index(date_str)
        test_date = tradeDates[test_end_idx - days]
        # 区间披露盈余公告
        period_reports = self.reports[self.reports['m_anntime'] == test_date]
        period_forecast = self.forecast_all[self.forecast_all['declare_date'] == test_date]
        period_express = self.express_all[self.express_all['declare_date'] == test_date]

        valid_candidates = []
        if not period_reports.empty:
            for row in range(period_reports.shape[0]):
                code = period_reports.iloc[row]['stock_code']
                info_date = period_reports.iloc[row]['m_anntime'] #披露日期
                if (all_raise(code, info_date, adj_all, days, num_experts=5) or overExpect_in_title(code, info_date, self.title_overExpect, days)) or big_increase(code, info_date, self.reports_dict) and not is_st(code, date_str):
                    valid_candidates.append(code)
        if not period_forecast.empty:
            for row in range(period_forecast.shape[0]):
                code = period_forecast.iloc[row]['stock_code_normal']
                info_date = period_forecast.iloc[row]['declare_date'] #披露日期
                period_forecast_stock = period_forecast.iloc[row]
                if (all_raise(code, info_date, adj_all, days, num_experts=5) or overExpect_in_title(code, info_date, title_overExpect, days)) or big_increase_forecast(code, info_date, period_forecast_stock, self.reports_dict) and not is_st(code, date_str) and code not in valid_candidates:
                    valid_candidates.append(code)
        if not period_express.empty:
            for row in range(period_express.shape[0]):
                code = period_express.iloc[row]['stock_code_normal']
                info_date = period_express.iloc[row]['declare_date'] #披露日期
                if (all_raise(code, info_date, adj_all, days, num_experts=5) or overExpect_in_title(code, info_date, title_overExpect, days)) and not is_st(code, date_str) and code not in valid_candidates:
                    valid_candidates.append(code)
        # 加入新的跟踪股
        for stock in valid_candidates:
            if stock not in self.trackingDict.keys():
                self.trackingDict[stock] = np.nan # initialize
                self.trackingDict_entry[stock] = date

        # 更新天数
        for stock in self.trackingDict.keys():
            # 最新业绩预告
            forecast_stk = self.forecast_all[(self.forecast_all['stock_code_normal'] == stock) & (self.forecast_all['declare_date'] <= date_str)]
            appo_rele_stk = self.appo_rele_date[(self.appo_rele_date['stock_code_normal'] == stock) & (self.appo_rele_date['appo_rele_date'] <= date_str)]
            try:
                report_stk = self.reports_dict[stock]['Income']
            except KeyError:
                print(stock, 'not in reports_dict')
                continue
            report_stk = report_stk[report_stk['m_anntime'] <= date_str]

            if not forecast_stk.empty and not appo_rele_stk.empty and not report_stk.empty:
                forecast_latest = convert_period((forecast_stk['report_year'].iloc[-1]), (forecast_stk['report_period'].iloc[-1]), 'forecast')
                appo_rele_latest = convert_period((appo_rele_stk['report_year'].iloc[-1]), (appo_rele_stk['report_quarter'].iloc[-1]), 'appo_rele')
                report_latest = report_stk.iloc[-1]['m_timetag']
                latest_date_str = max(forecast_latest, appo_rele_latest, report_latest)
                latest_date = pd.to_datetime(latest_date_str, format='%Y%m%d')
                if latest_date == report_latest: # Phase III
                    report_date = pd.to_datetime(report_stk.iloc[-1]['m_anntime'], format='%Y%m%d')
                    self.trackingDict[stock] = report_date - date
                elif latest_date == appo_rele_latest: # Phase II
                    rele_date = appo_rele_stk['appo_rele_date'].iloc[-1]
                    self.trackingDict[stock] = rele_date - date
                elif latest_date == forecast_latest: # Phase I
                    self.trackingDict[stock] = np.nan
        
        # 删除旧的股票
        for stock in list(self.trackingDict.keys()):
            if self.trackingDict_entry[stock] < date - pd.Timedelta(days=360):
                self.trackingDict.pop(stock)
                self.trackingDict_entry.pop(stock)


    def rate(self, stockList:list, date:str) -> list:
        # 多因子等权打分
        # SUE, DeltaROEQ, NPAdjustRate, AOG, HIGH250, totalMV
        SUE_list = []
        DeltaROEQ_list = []
        NPAdjustRate_list = []
        AOG_list = []
        HIGH250_list = []
        totalMV_list = []
        for stock in stockList:
            SUE_list.append(SUE(stock, date, 8, self.reports_dict))
            DeltaROEQ_list.append(DeltaROEQ(stock, date, PershareIndex_dict))
            NPAdjustRate_list.append(NPAdjustRate(stock, date, adj_all))
            AOG_list.append(AOG(stock, date, reports, forecast_all, express_all, price_data, zz500, tradeDates, tradeDates_ts))
            HIGH250_list.append(HIGH250(stock, date, reports, forecast_all, express_all, price_data, zz500, tradeDates, tradeDates_ts))
            totalMV_list.append(totalMV(stock, date, price_data, capital_dict))
        # 打分
        SUE_ranking_list = get_ranking(SUE_list, False)
        DeltaROEQ_ranking_list = get_ranking(DeltaROEQ_list, False)
        NPAdjustRate_ranking_list = get_ranking(NPAdjustRate_list, False)
        AOG_ranking_list = get_ranking(AOG_list, False)
        HIGH250_ranking_list = get_ranking(HIGH250_list, True)
        totalMV_ranking_list = get_ranking(totalMV_list, True)
        # 综合
        score_df = pd.DataFrame({'stock':stockList, 'SUE':SUE_ranking_list, 'DeltaROEQ':DeltaROEQ_ranking_list, 'NPAdjustRate':NPAdjustRate_ranking_list, 'AOG':AOG_ranking_list, 'HIGH250':HIGH250_ranking_list, 'totalMV':totalMV_ranking_list})
        score_df['score'] = score_df[['SUE', 'DeltaROEQ', 'NPAdjustRate', 'AOG', 'HIGH250', 'totalMV']].sum(axis=1)
        score_df.sort_values('score', ascending=False, inplace=True)
        return score_df['stock'].tolist()
    
    def get_candidate(self, target_num:int, date:str) -> list:
        # 先分档
        level1 = []
        level2 = []
        level3 = []
        for stock in list(self.trackingDict.keys()):
            if is_st(stock, date):
                self.trackingDict.pop(stock)
                self.trackingDict_entry.pop(stock)
                continue
            if self.trackingDict[stock] > 20 or np.isnan(self.trackingDict[stock]) or self.trackingDict[stock] < 0:
                level3.append(stock)
            elif self.trackingDict[stock] > 10:
                level2.append(stock)
            else:
                level1.append(stock)

        if len(level1) < target_num:
            # 第一档不够
            num_to_get2 = target_num - len(level1)
            if len(level2) >= num_to_get2:
                rated_level2 = self.rate(level2, date)
                candidates = level1 + rated_level2[:num_to_get2]
            else:
                # 第二档也不够
                num_to_get3 = num_to_get2 - len(level2)
                if len(level3) >= num_to_get3:
                    rated_level2 = self.rate(level2, date)
                    rated_level3 = self.rate(level3, date)
                    candidates = level1 + rated_level2 + rated_level3[:num_to_get3]
                else:
                    # 第三档也不够
                    candidates = level1 + level2 + level3
        else:
            # 第一档够
            rated_level1 = self.rate(level1, date)
            candidates = rated_level1[:target_num]
        
        '''
        for stock in candidates:
            self.trackingDict.pop(stock)
            self.trackingDict_entry.pop(stock)'''
        return candidates

# ==========================================================================================================================================
if __name__ == '__main__':
    print('--------------------------start--------------------------------')
    track = track(appo_rele_date, reports, reports_dict, forecast_all, express_all, adj_all, title_overExpect, price_data, zz500, tradeDates, tradeDates_ts, capital_dict, PershareIndex_dict)
    start_date = '20200101'
    end_date = '20240701'
    tracked_portfolio = {}
    tradeDates_track = [date for date in tradeDates if date >= start_date and date <= end_date]
    i = 0
    for date in tqdm(tradeDates_track):
        track.update_trackingDict(date, 5)
        tracked_portfolio[date] = track.get_candidate(100, date)
        if (i+1) % 100 == 0:
            print('=============================SAVING==============================')
            with open(f'C:/Users/stansfield/Documents/Coding/OverExpect/growth_Period/output/tracked_portfolio_{date}.json', 'w') as f:
                json.dump(tracked_portfolio, f)
            with open(f'C:/Users/stansfield/Documents/Coding/OverExpect/growth_Period/output/trackingDict_{date}.json', 'w') as f:
                json.dump(track.trackingDict, f)
        i += 1
    # 保存
    with open('C:/Users/stansfield/Documents/Coding/OverExpect/growth_Period/output/tracked_portfolio.json', 'w') as f:
        json.dump(tracked_portfolio, f)