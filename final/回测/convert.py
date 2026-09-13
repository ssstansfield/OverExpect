import json
import pandas as pd
with open (r'C:\Users\stansfield\Documents\Coding\OverExpect\final\回测\tracked_portfolio.json', 'r') as f:
    portfolio_dict = json.load(f)
# 对portfolio_dict按照key进行排序
portfolio_dict = dict(sorted(portfolio_dict.items(), key=lambda x: x[0]))
# 找出最长的股票列表长度
max_length = max(len(stocks) for stocks in portfolio_dict.values())

# 创建 DataFrame 并填充数据
df = pd.DataFrame({date: stocks + [None]*(max_length - len(stocks)) for date, stocks in portfolio_dict.items()}).T

# 设置索引名称
df.index.name = 'Date'
df.sort_index(inplace=True)
df.reset_index(inplace=True)
df.to_csv('portfolio_track.csv',index=False)