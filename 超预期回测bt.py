import rqdatac
rqdatac.init('15805988503', 'Ss888888')
import numpy as np
import pandas as pd
import datetime as dt
import os
import matplotlib.pyplot as plt
from tqdm import tqdm, tnrange
import json
import datetime
import backtrader as bt # 导入 Backtrader
import backtrader.indicators as btind # 导入策略分析模块
import backtrader.feeds as btfeeds # 导入数据模块

# 全A股数据
all_gotPrice = pd.read_csv(r'C:\Users\stansfield\Documents\Coding\OverExpect\all_gotPrice.csv')
all_gotPrice['date'] = pd.to_datetime(all_gotPrice['date'])
# 中证500数据
zz500 = pd.read_csv(r'C:\Users\stansfield\Documents\Coding\OverExpect\zz500.csv')
zz500.reset_index(inplace=True)
zz500['date'] = pd.to_datetime(zz500['date'])
# 交易日
tradeDates = all_gotPrice['date'].unique()
tradeDates = pd.to_datetime(tradeDates)
tradeDates.sort_values()
# 代码调整
adjust_codes = []
for code in tqdm(all_gotPrice['order_book_id']):
    adjust_code = code.split('.')[0]
    adjust_codes.append(adjust_code)
all_gotPrice['stk_code'] = adjust_codes


daily_price_bt = pd.DataFrame({'datetime': all_gotPrice['date'], 'order_book_id': all_gotPrice['order_book_id'],'open': all_gotPrice['open'], 'high': all_gotPrice['high'], 'low': all_gotPrice['low'], 'close': all_gotPrice['close'], 'volume': all_gotPrice['volumn']})
daily_price_bt['openinterest'] = [0]*daily_price_bt.shape[0]
daily_price_bt = daily_price_bt[daily_price_bt['datetime'] >= '2019-01-31']
daily_price_bt.set_index('datetime', inplace=True)

trade_info = pd.read_csv(r'C:\Users\stansfield\Documents\Coding\OverExpect\portfolio_bt.csv')

zz500_bt = pd.DataFrame({'datetime': zz500['date'], 'open': zz500['open'], 'high': zz500['high'], 'low': zz500['low'], 'close': zz500['close'], 'volume': zz500['volume']})
zz500_bt['openinterest'] = [0]*zz500_bt.shape[0]
zz500_bt = zz500_bt[zz500_bt['datetime'] >= '2019-01-31']
zz500_bt.set_index('datetime', inplace=True)

start_date = pd.to_datetime('2019-01-31')
end_date = pd.to_datetime('2024-05-16')

# 创建策略
class TestStrategy(bt.Strategy):
    '''选股策略'''
    def __init__(self, trade_info):
        self.buy_stock = trade_info # 保留调仓列表
        # 读取调仓日期，即每月的最后一个交易日，回测时，会在这一天下单，然后在下一个交易日，以开盘价买入
        self.trade_dates = pd.to_datetime(self.buy_stock['trade_date'].unique()).tolist()
        self.order_list = [] # 记录以往订单，方便调仓日对未完成订单做处理
        self.buy_stocks_pre = [] # 记录上一期持仓
    def next(self):
        dt = self.datas[0].datetime.date(0) # 获取当前的回测时间点
        print("当前时间点：", dt)
        # 如果是调仓日，则进行调仓操作
        if dt in self.trade_dates:
            print("--------------{} 为调仓日----------".format(dt))
            # 在调仓之前，取消之前所下的没成交也未到期的订单
            if len(self.order_list) > 0:
                for od in self.order_list:
                    self.cancel(od) # 如果订单未完成，则撤销订单
                self.order_list = [] #重置订单列表
            # 提取当前调仓日的持仓列表
            buy_stocks_data = self.buy_stock.query(f"trade_date=='{dt}'")
            long_list = buy_stocks_data['sec_code'].tolist()
            print('long_list', long_list) # 打印持仓列表
            # 对现有持仓中，调仓后不再继续持有的股票进行卖出平仓
            sell_stock = [i for i in self.buy_stocks_pre if i not in long_list]
            print('sell_stock', sell_stock) # 打印平仓列表
            if len(sell_stock) > 0:
                print("-----------对不再持有的股票进行平仓--------------")
                for stock in sell_stock:
                    data = self.getdatabyname(stock)
                    if self.getposition(data).size > 0 :
                        od = self.close(data=data)
                        self.order_list.append(od) # 记录卖出订单
            # 买入此次调仓的股票：多退少补原则
            print("-----------买入此次调仓期的股票--------------")
            for stock in long_list:
                w = buy_stocks_data.query(f"sec_code=='{stock}'")['weight'].iloc[0] # 提取持仓权重
                data = self.getdatabyname(stock)
                order = self.order_target_percent(data=data, target=w*0.95) # 为减少可用资金不足的情况，留 5% 的现金做备用
                self.order_list.append(order)
       
            self.buy_stocks_pre = long_list # 保存此次调仓的股票列表
        
# 实例化 cerebro
cerebro = bt.Cerebro()
# 添加策略
cerebro.addstrategy(TestStrategy, trade_info=trade_info)


# 加上市场数据
for stock in tqdm(daily_price_bt['order_book_id'].unique()):
    # 日期对齐
    data = pd.DataFrame(index=daily_price_bt.index.unique()) # 获取回测区间内所有交易日
    df = daily_price_bt.query(f"order_book_id=='{stock}'")[['open','high','low','close','volume','openinterest']]
    data_ = pd.merge(data, df, left_index=True, right_index=True, how='left')
    # 缺失值处理：日期对齐时会使得有些交易日的数据为空，所以需要对缺失数据进行填充
    data_.loc[:,['volume','openinterest']] = data_.loc[:,['volume','openinterest']].fillna(0)
    data_.loc[:,['open','high','low','close']] = data_.loc[:,['open','high','low','close']].fillna(method='pad')
    data_.loc[:,['open','high','low','close']] = data_.loc[:,['open','high','low','close']].fillna(0)
    # 导入数据
    datafeed = bt.feeds.PandasData(dataname=data_, fromdate=start_date, todate=end_date)
    cerebro.adddata(datafeed, name=stock) # 通过 name 实现数据集与股票的一一对应

# 设置中证500为benchmark
data_ = zz500_bt
# 缺失值处理：日期对齐时会使得有些交易日的数据为空，所以需要对缺失数据进行填充
data_.loc[:,['volume','openinterest']] = data_.loc[:,['volume','openinterest']].fillna(0)
data_.loc[:,['open','high','low','close']] = data_.loc[:,['open','high','low','close']].fillna(method='pad')
data_.loc[:,['open','high','low','close']] = data_.loc[:,['open','high','low','close']].fillna(0)
# 导入数据
benchmark = bt.feeds.PandasData(dataname=data_, fromdate=start_date, todate=end_date)
cerebro.adddata(benchmark, name='CSI 500')
cerebro.addobserver(bt.observers.Benchmark, data=benchmark)

# 通过经纪商设置初始资金
cerebro.broker.setcash(1000000.0)
# 设置交易佣金
cerebro.broker.setcommission(0.003)
# 设置滑点
cerebro.broker.set_slippage_perc(perc=0.0001)

# 添加分析器
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='pnl') # 返回收益率时序数据
cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn') # 年化收益率
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='_SharpeRatio') # 夏普比率
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='_DrawDown') # 回撤
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='_TimeReturn')

result = cerebro.run()
print('done')
# 可视化回测结果
#cerebro.plot()

# 从返回的 result 中提取回测结果
strat = result[0]
# 返回日度收益率序列
daily_return = pd.Series(strat.analyzers.pnl.get_analysis())
# 打印评价指标
print("--------------- AnnualReturn -----------------")
print(strat.analyzers._AnnualReturn.get_analysis())
print("--------------- SharpeRatio -----------------")
print(strat.analyzers._SharpeRatio.get_analysis())
print("--------------- DrawDown -----------------")
print(strat.analyzers._DrawDown.get_analysis())


# 提取收益序列
pnl = pd.Series(result[0].analyzers._TimeReturn.get_analysis())
# 计算累计收益
cumulative = (pnl + 1).cumprod()
# 计算回撤序列
max_return = cumulative.cummax()
drawdown = (cumulative - max_return) / max_return

# 计算收益评价指标
import pyfolio as pf
# 按年统计收益指标
perf_stats_year = (pnl).groupby(pnl.index.to_period('y')).apply(lambda data: pf.timeseries.perf_stats(data)).unstack()
# 统计所有时间段的收益指标
perf_stats_all = pf.timeseries.perf_stats((pnl)).to_frame(name='all')
perf_stats = pd.concat([perf_stats_year, perf_stats_all.T], axis=0)
perf_stats_ = round(perf_stats,4).reset_index()


# 绘制图形
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
import matplotlib.ticker as ticker # 导入设置坐标轴的模块
#plt.style.use('seaborn') 
#plt.style.use('dark_background')

fig, (ax0, ax1) = plt.subplots(2,1, gridspec_kw = {'height_ratios':[1.5, 4]}, figsize=(20,8))
cols_names = ['date', 'Annual\nreturn', 'Cumulative\nreturns', 'Annual\nvolatility',
             'Sharpe\nratio', 'Calmar\nratio', 'Stability', 'Max\ndrawdown',
             'Omega\nratio', 'Sortino\nratio', 'Skew', 'Kurtosis', 'Tail\nratio',
             'Daily value\nat risk']

# 绘制表格
ax0.set_axis_off() # 除去坐标轴
table = ax0.table(cellText = perf_stats_.values,
                bbox=(0,0,1,1), # 设置表格位置， (x0, y0, width, height)
                rowLoc = 'right', # 行标题居中
                cellLoc='right' ,
                colLabels = cols_names, # 设置列标题
                colLoc = 'right', # 列标题居中
                edges = 'open' # 不显示表格边框
                )
table.set_fontsize(13)

# 绘制累计收益曲线
ax2 = ax1.twinx()
ax1.yaxis.set_ticks_position('right') # 将回撤曲线的 y 轴移至右侧
ax2.yaxis.set_ticks_position('left') # 将累计收益曲线的 y 轴移至左侧
# 绘制回撤曲线
drawdown.plot.area(ax=ax1, label='drawdown (right)', rot=0, alpha=0.3, fontsize=13, grid=False)
# 绘制累计收益曲线
(cumulative).plot(ax=ax2, color='#F1C40F' , lw=3.0, label='cumret (left)', rot=0, fontsize=13, grid=False)
# 不然 x 轴留有空白
ax2.set_xbound(lower=cumulative.index.min(), upper=cumulative.index.max())
# 主轴定位器：每 5 个月显示一个日期：根据具体天数来做排版
ax2.xaxis.set_major_locator(ticker.MultipleLocator(100))
# 同时绘制双轴的图例
h1,l1 = ax1.get_legend_handles_labels()
h2,l2 = ax2.get_legend_handles_labels()
plt.legend(h1+h2,l1+l2, fontsize=12, loc='upper left', ncol=1)

fig.tight_layout() # 规整排版
plt.show()

b = cerebro.plot()
b[0][0]
b[0][0].savefig(r'C:\Users\stansfield\Documents\Coding\OverExpect\bt.png')