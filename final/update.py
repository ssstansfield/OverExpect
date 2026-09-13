from xtquant import xtdatacenter as xtdc
xtdc.set_token('545fbf3493e048987056052b2d1988e5574fab15')

# 设置数据存储路径
xtdc.set_data_home_dir('D:/XTdata') 
xtdc.init()
# 导入 xtdata
from xtquant import xtdata

from tqdm import tqdm
import time

# 获取交易日期
tradeDates = xtdata.get_trading_calendar(market='SH', start_time='20190101', end_time='20300101')

# 获取板块列表
stockList = xtdata.get_stock_list_in_sector('沪深A股')

def my_download(stock_list,period,start_date = '', end_date = ''):
    '''
    用于显示下载进度
    '''
    if "d" in period:
        period = "1d"
    elif "m" in period:
        if int(period[0]) < 5:
            period = "1m"
        else:
            period = "5m"
    elif "tick" == period:
        pass
    else:
        raise KeyboardInterrupt("周期传入错误")

    for i in tqdm(stock_list):
        xtdata.download_history_data(i,period,start_date, end_date)
    print("下载任务结束")

def do_subscribe_quote(stock_list:list, period:str):
        for i in tqdm(stock_list):
                xtdata.subscribe_quote(i,period = period)
        time.sleep(1) # 等待订阅完成

if __name__ == "__main__":

    start_date = '20190101'# 格式"YYYYMMDD"，开始下载的日期，date = ""时全量下载
    end_date = "" 
    period = "1d"

    need_download = 0  # 取数据是空值时，将need_download赋值为1，确保正确下载了历史数据
    code_list = stockList # 股票列表

    if need_download: # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
        my_download(code_list, period, start_date, end_date)

    # 获取财务数据
    xtdata.download_financial_data(stockList, table_list=['Balance', 'Income', 'CashFlow', 'PershareIndex', 'Capital'], start_time = '20090101', end_time = '')

    # 更新股票数据
    stockList = xtdata.get_stock_list_in_sector('沪深A股')
    do_subscribe_quote(stockList, period = "1d")