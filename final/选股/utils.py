# imports
import pandas as pd
import numpy as np


# stk_code 在 info_date 披露后5天内至少有1篇研报标题超预期
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