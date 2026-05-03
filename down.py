import efinance as ef
from empyrical import max_drawdown
import numpy as np
import pandas as pd

fund_num='015599'

# his_data = ef.fund.get_quote_history(fund_num)

# his_data.to_csv(rf'{fund_num}.csv')


now = ef.fund.get_realtime_increase_rate(['011840','013180','015599'])
print(now.to_)
