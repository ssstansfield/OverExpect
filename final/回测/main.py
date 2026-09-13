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
import json
from copy import copy
from collections import deque
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
# ==================================基础数据==================================
stockList = xtdata.get_stock_list_in_sector('沪深A股')
count = -1
price_data = xtdata.get_market_data_ex([],stockList, period='1d', start_time='20190101', end_time='', dividend_type='back_ratio')
all_gotPrice = pd.DataFrame()
for stock in tqdm_notebook(price_data.keys()):
    try:
        price = price_data[stock]
    except KeyError:
        continue
    price['stock_code'] = [stock] * len(price)
    all_gotPrice = pd.concat([all_gotPrice, price])
all_gotPrice.reset_index(inplace=True)
all_gotPrice.rename(columns={'index':'Date'}, inplace=True)

# ===================================回测===================================
class context(object):
    def __init__(self, all_gotPrice, tradeDates):
        self.portfolio_dq = deque() # 用 deque 存储股票池, 左出右进
        self.portfolio = {}
        self.event_log = pd.DataFrame(columns=['date', 'stock', 'event'])
        self.start_date = '20190426'
        self.end_date = '20240613'
        self.cash = 10000000
        self.split_num = 200 #初始资金分成n份建仓
        self.init_cash = copy(self.cash)
        self.commision = 0.003
        self.tax = 0.001
        self.tradeDates = tradeDates[tradeDates.get_loc(self.start_date):tradeDates.get_loc(self.end_date)+1]
        self.all_gotPrice = all_gotPrice

    def buy(self, stock, date, num, prices:pd.DataFrame):
        #prices = self.all_gotPrice[(self.all_gotPrice['order_book_id'] == stock) & (self.all_gotPrice['date'] == date)]
        if prices.empty:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['无数据']})], axis=0)
            return False
        open_price = prices['open']
        high_price = prices['high']
        low_price = prices['low']
        close_price = prices['close']
        average_price = (open_price + high_price + low_price + close_price) / 4

        if open_price == high_price == low_price == close_price:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['涨跌停']})], axis=0)
            return False
        if num * average_price > self.cash:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['资金不足']})], axis=0)
            return False
        if is_st(stock, date):
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['ST']})], axis=0)
            return False
        else:
            self.cash -= num * average_price * (1 + self.commision)
            if stock in self.portfolio:
                self.portfolio[stock] += num
            else:
                self.portfolio[stock] = num
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': [f'买入{num}']})], axis=0)
            return True
        
    def buy_value(self, stock, date, value, prices:pd.DataFrame):
        #prices = self.all_gotPrice[(self.all_gotPrice['order_book_id'] == stock) & (self.all_gotPrice['date'] == date)]
        if prices.empty:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['无数据']})], axis=0)
            return False
        open_price = prices['open']
        high_price = prices['high']
        low_price = prices['low']
        close_price = prices['close']
        average_price = (open_price + high_price + low_price + close_price) / 4
        target_num = value / average_price
        if stock in self.portfolio:
            if stock[0:3] == '688': # 科创板200股起买
                num = 200 + 100 * ((target_num - self.portfolio[stock] - 200) // 100)
                if num <= 200:
                    self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['科创板不足200']})], axis=0)
                    return False
            else:
                num = 100 * ((target_num - self.portfolio[stock]) // 100)
                if num == 0:
                    self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['不足100']})], axis=0)
                    return False
                elif num < 0:
                    self.sell(stock, date, -num, prices)
                    return True
        else:
            if stock[0:3] == '688': #科创板200股起买
                num = 200 + 100 * ((target_num - 200) // 100)
                if num < 200:
                    self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['科创板不足200']})], axis=0)
                    return False
            else:
                num = 100 * (target_num // 100)
                if num == 0:
                    self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['不足100']})], axis=0)
                    return False
            
        value = num * average_price

        if open_price == high_price == low_price == close_price:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['涨跌停']})], axis=0)
            return False
        if value > self.cash:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['资金不足']})], axis=0)
            return False
        if is_st(stock, date):
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['ST']})], axis=0)
            return False
        else:
            self.cash -= value * (1 + self.commision)
            if stock in self.portfolio:
                self.portfolio[stock] += num
            else:
                self.portfolio[stock] = num
                self.portfolio_dq.append(stock)
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': [f'买入{num}']})], axis=0)
            return True

    def sell(self, stock, date, num, prices:pd.DataFrame):
        #prices = self.all_gotPrice[(self.all_gotPrice['order_book_id'] == stock) & (self.all_gotPrice['date'] == date)]
        if prices.empty:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['无数据']})], axis=0)
            return False
        open_price = prices['open']
        high_price = prices['high']
        low_price = prices['low']
        close_price = prices['close']
        average_price = (open_price + high_price + low_price + close_price) / 4

        if open_price == high_price == low_price == close_price:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['涨跌停']})], axis=0)
            return False
        if stock not in self.portfolio:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['未持有']})], axis=0)
            return False
        else:
            self.cash += num * average_price * (1 - self.commision - self.tax)
            self.portfolio[stock] -= num
            if self.portfolio[stock] == 0:
                self.portfolio.pop(stock)
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': [f'卖出{num}']})], axis=0)
            return True

    def clear_stock(self, stock, date, prices:pd.DataFrame):
        if prices.empty:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['无数据']})], axis=0)
            return False
        open_price = prices['open']
        high_price = prices['high']
        low_price = prices['low']
        close_price = prices['close']
        average_price = (open_price + high_price + low_price + close_price) / 4
        if open_price == high_price == low_price == close_price:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['涨跌停']})], axis=0)
            return False
        if stock not in self.portfolio:
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['未持有']})], axis=0)
            return False
        else:
            num = self.portfolio[stock]
            free_cash = num * average_price * (1 - self.commision - self.tax)
            self.cash += free_cash
            self.portfolio.pop(stock)
            self.event_log = pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': [f'卖出{num}']})], axis=0)
            return free_cash

    def get_portfolio_value(self, date):
        # 提取指定日期的所有价格数据，并将 `order_book_id` 设置为索引
        prices_on_date = self.all_gotPrice[self.all_gotPrice['Date'] == date].set_index('stock_code')['close']
        
        portfolio_value = self.cash
        for stock, quantity in self.portfolio.items():
            # 直接从已设置好索引的 Series 中获取价格
            try:
                close_price = prices_on_date[stock]
                portfolio_value += quantity * close_price
            except KeyError:
                print(f'{stock}在{date}停牌')
                continue
            except Exception as e:
                print(f'get_portfolio_value中{stock}在{date}出现{e}')
                continue
        return portfolio_value
    
    def get_portfolio_proportion(self, date):
        # 提取指定日期的所有价格数据，并将 `order_book_id` 设置为索引
        prices_on_date = self.all_gotPrice[self.all_gotPrice['Date'] == date].set_index('stock_code')['close']
        
        portfolio_value = self.get_portfolio_value(date)
        portfolio_proportion = {}
        for stock, quantity in self.portfolio.items():
            # 直接从已设置好索引的 Series 中获取价格
            try:
                close_price = prices_on_date[stock]
                stock_value = quantity * close_price
                stock_proportion = stock_value / portfolio_value
                portfolio_proportion[stock] = stock_proportion
            except KeyError:
                print(f'{stock}在{date}停牌')
                continue
            except Exception as e:
                print(f'get_portfolio_proportion中{stock}在{date}出现{e}')
                continue
        return portfolio_proportion

    def adjust_portfolio(self, date, targetList: list):
        prices_date = self.all_gotPrice[self.all_gotPrice['Date'] == date].set_index('stock_code')
        while len(targetList) > 0 and self.cash > self.init_cash/self.split_num: # 还没满仓，初始资金还有剩余
            stock = targetList.pop(0)
            try:
                price_stock = prices_date.loc[stock]
            except KeyError:
                print(f'{stock}在{date}停牌')
                pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock], 'event': ['停牌']})], axis=0)
                continue
            except Exception as e:
                print(f'adjust_portfolio中{stock}在{date}出现{e}')
                continue
            self.buy_value(stock, date, self.init_cash/self.split_num, price_stock)
        
        while len(targetList) > 0: # 满仓后还有剩余股票
            # 卖出，清出仓位
            stock_to_sell = self.portfolio_dq.popleft()
            try:
                price_sell = prices_date.loc[stock_to_sell]
            except KeyError:
                print(f'{stock_to_sell}在{date}停牌')
                pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock_to_sell], 'event': ['停牌']})], axis=0)
                continue
            except Exception as e:
                print(f'adjust_portfolio中{stock_to_sell}在{date}出现{e}')
                continue
            free_cash = self.clear_stock(stock_to_sell, date, price_sell)
            # 用空出资金买入
            stock_to_buy = targetList.pop(0)
            try:
                price_buy = prices_date.loc[stock_to_buy]
            except KeyError:
                print(f'{stock_to_buy}在{date}停牌')
                pd.concat([self.event_log, pd.DataFrame({'date': [date], 'stock': [stock_to_buy], 'event': ['停牌']})], axis=0)
                continue
            except Exception as e:
                print(f'adjust_portfolio中{stock_to_buy}在{date}出现{e}')
                continue
            self.buy_value(stock_to_buy, date, free_cash, price_buy)


if __name__ == '__main__':
    portfolio_values = []
    portfolio_history = {}
    portfolio_proportions = []
    tradeDates = xtdata.get_trading_calendar(market='SH', start_time='20190101', end_time='20300101')
    tradeDates = pd.Index(tradeDates)
    tradeDates_ts = pd.Index([pd.Timestamp(date) for date in tradeDates])
    portfolio_df = pd.read_csv('portfolio_dailyDf_0426.csv')
    adj_dates = portfolio_df['Date'].tolist()
    adjusted_adj_dates = [find_nearest_trading_date(tradeDates_ts, date, latter=True)[0] for date in portfolio_df['Date'].tolist()[:-1]]
    context = context(all_gotPrice, tradeDates)
    for date in tqdm_notebook(context.tradeDates):
        if date in adjusted_adj_dates: #调仓日
            adj_date = adj_dates[adjusted_adj_dates.index(date)]
            targetList = [stock for stock in portfolio_df.loc[portfolio_df['Date'] == adj_date].values.tolist()[0][1:] if type(stock) == str]
            context.adjust_portfolio(date, targetList)
            #portfolio_proportions.append(context.get_portfolio_proportion(date))
            portfolio_history[date] = copy(context.portfolio)
        portfolio_values.append(context.get_portfolio_value(date))

    zz500 = xtdata.get_market_data_ex([],['000905.SH'], period='1d', start_time='20190101', end_time='')['000905.SH']
    zz500.reset_index(inplace=True)
    zz500.rename(columns={'index':'Date'}, inplace=True)
    zz500 = zz500[(zz500['Date'] >= context.start_date) & (zz500['Date'] <= context.end_date)]
    zz500_adj = (zz500['close']/zz500['close'].values[0])*context.init_cash
    plt.figure(figsize=(20, 10), dpi=150)
    dates = pd.to_datetime(context.tradeDates, format='%Y%m%d')
    plt.plot(dates, portfolio_values, label='portfolio_value', color='red', alpha=0.3)
    plt.plot(dates, zz500_adj, label='CSI500', color='blue', alpha=0.3)
    plt.plot(dates, (portfolio_values - zz500_adj), label='portfolio - CSI500', color='black')
    plt.legend()

    # ==================================绩效评估==================================
    interbank_offered_rate_monthAvg = pd.read_csv('interbank_offered_rate_monthAvg.csv')
    zz500['date'] = pd.to_datetime(zz500['Date'])
    zz500 = zz500[(zz500['date'] >= context.start_date) & (zz500['date'] <= context.end_date)]
    net_value_df = pd.DataFrame({'date': context.tradeDates, 'net_value': portfolio_values, 'CSI500': zz500['close']})
    net_value_df['date'] = pd.to_datetime(net_value_df['date'])
    net_value_df['year'] = net_value_df['date'].dt.year
    net_value_df['month'] = net_value_df['date'].dt.month
    net_value_df['week'] = net_value_df['date'].dt.week
    net_value_df.to_csv('net_value_df.csv', index=False)

    portfolio_returns = []
    index_returns = []
    relative_max_drawdowns = []
    max_drawdowns = []
    IRs = []
    tracking_errors = []
    win_rates = []
    Sortino_rates = []


    for year in tqdm_notebook(net_value_df['year'].unique()):
        # 计算收益率
        year_df = net_value_df[net_value_df['year'] == year]
        portfolio_returns.append(calculate_returns(year_df['net_value'].tolist())[-1])
        index_returns.append(calculate_returns(year_df['CSI500'].tolist())[-1])
        # 计算最大回撤
        portfolio_adj = np.array(year_df['net_value']) / year_df['net_value'].values[0]
        index_adj = np.array(year_df['CSI500']) / year_df['CSI500'].values[0]
        relative_max_drawdowns.append(calculate_max_drawdown(portfolio_adj/index_adj))
        max_drawdowns.append(calculate_max_drawdown(year_df['net_value']))
        # 计算跟踪误差
        tracking_error = calculate_tracking_error(year_df['net_value'], year_df['CSI500'])
        tracking_errors.append(tracking_error)
        # 计算信息比率
        IRs.append(calculate_information_ratio(year_df['net_value'].tolist(), year_df['CSI500'].tolist(), tracking_error))
        # 计算胜率
        win_week = 0
        for week in year_df['week'].unique():
            week_df = year_df[year_df['week'] == week]
            portfolio_weekly_return = calculate_returns(week_df['net_value'].tolist())[-1]
            index_weekly_return = calculate_returns(week_df['CSI500'].tolist())[-1]
            if portfolio_weekly_return > index_weekly_return:
                win_week += 1
        win_rates.append(win_week / len(year_df['week'].unique()))
        # 计算月度Sortino比率
        risk_premium = 0
        downside_returns = []
        for month in year_df['month'].unique():
            month_df = year_df[year_df['month'] == month]
            rf = 0.01*interbank_offered_rate_monthAvg[(interbank_offered_rate_monthAvg['year'] == year) & (interbank_offered_rate_monthAvg['month'] == month)]['1M'].values[0]
            portfolio_monthly_return = calculate_returns(month_df['net_value'].tolist())[-1]
            risk_premium += (portfolio_monthly_return - rf)
            if portfolio_monthly_return < 0:
                downside_returns.append(portfolio_monthly_return)
        downside_risk_std = np.sqrt(sum([r**2 for r in downside_returns])/len(year_df['month'].unique()))
        Sortino_rates.append(risk_premium / downside_risk_std)

    excess_returns = pd.Series(portfolio_returns) - pd.Series(index_returns)
    performance_df = pd.DataFrame({'年份': net_value_df['year'].unique(), '组合收益率': portfolio_returns, '指数收益率': index_returns, '超额收益率': excess_returns, '相对最大回撤': relative_max_drawdowns, '绝对最大回撤': max_drawdowns, '信息比率': IRs, '跟踪误差': tracking_errors, '胜率': win_rates, 'Sortino比率': Sortino_rates})
    performance_df.to_csv('performance_df.csv', index=False)
