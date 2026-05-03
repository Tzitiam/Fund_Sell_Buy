"""
百分位分析模块（修正版）
正确计算百分位：当前净值是历史最高时返回100%
"""

import pandas as pd
import os


class PercentileAnalyzer:
    """净值百分位分析器"""
    
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.df = None
        self.load_data()
    
    def load_data(self):
        if not os.path.exists(self.csv_file):
            print(f"文件不存在: {self.csv_file}")
            return False
        
        self.df = pd.read_csv(self.csv_file)
        if '日期' in self.df.columns:
            self.df['日期'] = pd.to_datetime(self.df['日期'])
            self.df = self.df.sort_values('日期')
        
        return True
    
    def get_current_percentile(self):
        """
        获取当前净值的历史百分位
        
        规则：
        - 历史最高 → 100%
        - 历史最低 → 0%
        - 其他 → (小于等于当前值的数量) / 总数 * 100
        """
        if self.df is None or self.df.empty:
            return None
        
        nav_series = self.df['单位净值'].dropna()
        current_nav = nav_series.iloc[-1]
        
        # 检查是否历史最高
        if current_nav >= nav_series.max():
            return 100.00
        
        # 检查是否历史最低
        if current_nav <= nav_series.min():
            return 0.00
        
        # 计算小于等于当前值的数量
        count_le = (nav_series <= current_nav).sum()
        total = len(nav_series)
        
        percentile = count_le / total * 100
        
        return round(percentile, 2)


# 使用示例
if __name__ == "__main__":
    for code in ['011840', '013180', '015599']:
        analyzer = PercentileAnalyzer(f"{code}.csv")
        pct = analyzer.get_current_percentile()
        if pct is not None:
            print(f"{code}: {pct}%")