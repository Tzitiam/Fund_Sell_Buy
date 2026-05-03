"""
基金分析核心算法模块
功能：波峰波谷识别、交易信号生成、数据导出
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks


class MovingAveragePeakTroughFinder:
    """
    波峰波谷识别模块
    
    核心逻辑：
    1. 在平滑曲线上找候选极值点（过滤噪声）
    2. 在原始数据上，以候选点为中心前后各N天，找真正的最高/最低点
    3. 波谷→波峰涨幅 >= min_rise_pct 才算有效上涨波段
    4. 波峰→波谷跌幅 >= min_fall_pct 才算有效下跌波段
    """
    
    def __init__(self, ma_window=7, prominence_pct=0.015, min_distance=5, 
                 min_rise_pct=0.10, min_fall_pct=0.04, search_window=3):
        """
        参数:
            ma_window: 移动平均窗口大小（用于平滑过滤）
            prominence_pct: 显著性阈值（百分比）
            min_distance: 两个极值点之间的最小距离（天数）
            min_rise_pct: 波谷到波峰的最小涨幅（默认10%）
            min_fall_pct: 波峰到波谷的最小跌幅（默认4%）
            search_window: 在原始数据中搜索真实极值点的窗口大小
        """
        self.ma_window = ma_window
        self.prominence_pct = prominence_pct
        self.min_distance = min_distance
        self.min_rise_pct = min_rise_pct
        self.min_fall_pct = min_fall_pct
        self.search_window = search_window
    
    def smooth(self, prices):
        """移动平均平滑 - 仅用于辅助过滤"""
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)
        elif isinstance(prices, list):
            prices = pd.Series(prices)
        return prices.rolling(window=self.ma_window, min_periods=1).mean()
    
    def find_true_peaks_troughs(self, raw_prices, smoothed_values):
        """
        在原始数据上找真正的波峰波谷
        """
        n = len(raw_prices)
        
        # 在平滑曲线上找候选点
        rolling_avg = pd.Series(smoothed_values).rolling(window=min(20, n//3), min_periods=1).mean().values
        prominence_abs = rolling_avg * self.prominence_pct
        
        candidate_peaks, peaks_properties = find_peaks(
            smoothed_values, 
            prominence=prominence_abs, 
            distance=self.min_distance
        )
        candidate_troughs, troughs_properties = find_peaks(
            -smoothed_values, 
            prominence=prominence_abs, 
            distance=self.min_distance
        )
        
        # 在原始数据上找真正的波峰
        true_peaks = []
        for cp in candidate_peaks:
            left = max(0, cp - self.search_window)
            right = min(n, cp + self.search_window + 1)
            window = raw_prices[left:right]
            true_idx = left + np.argmax(window)
            true_value = raw_prices[true_idx]
            
            if true_peaks and abs(true_peaks[-1]['index'] - true_idx) < self.min_distance:
                if true_value > true_peaks[-1]['value']:
                    true_peaks[-1] = {'index': true_idx, 'value': true_value, 'type': 'peak'}
            else:
                true_peaks.append({'index': true_idx, 'value': true_value, 'type': 'peak'})
        
        # 在原始数据上找真正的波谷
        true_troughs = []
        for ct in candidate_troughs:
            left = max(0, ct - self.search_window)
            right = min(n, ct + self.search_window + 1)
            window = raw_prices[left:right]
            true_idx = left + np.argmin(window)
            true_value = raw_prices[true_idx]
            
            if true_troughs and abs(true_troughs[-1]['index'] - true_idx) < self.min_distance:
                if true_value < true_troughs[-1]['value']:
                    true_troughs[-1] = {'index': true_idx, 'value': true_value, 'type': 'trough'}
            else:
                true_troughs.append({'index': true_idx, 'value': true_value, 'type': 'trough'})
        
        # 合并并排序
        extremums = true_peaks + true_troughs
        extremums.sort(key=lambda x: x['index'])
        
        return extremums
    
    def filter_by_rise_fall_pct(self, extremums, raw_prices):
        """
        双向过滤：
        1. 波谷→波峰：涨幅必须 >= min_rise_pct
        2. 波峰→波谷：跌幅必须 >= min_fall_pct
        
        返回过滤后的极值点列表
        """
        if len(extremums) < 2:
            return extremums
        
        filtered = []
        i = 0
        
        while i < len(extremums):
            current = extremums[i]
            
            if current['type'] == 'trough':
                # 找下一个波峰
                next_peak = None
                next_idx = i + 1
                while next_idx < len(extremums):
                    if extremums[next_idx]['type'] == 'peak':
                        next_peak = extremums[next_idx]
                        break
                    next_idx += 1
                
                if next_peak:
                    # 检查涨幅
                    rise_pct = (next_peak['value'] - current['value']) / current['value']
                    if rise_pct >= self.min_rise_pct:
                        filtered.append(current)
                    else:
                        # 涨幅不足，跳过这个波谷和对应的波峰
                        i = next_idx
                        continue
                else:
                    filtered.append(current)
            
            elif current['type'] == 'peak':
                # 找下一个波谷
                next_trough = None
                next_idx = i + 1
                while next_idx < len(extremums):
                    if extremums[next_idx]['type'] == 'trough':
                        next_trough = extremums[next_idx]
                        break
                    next_idx += 1
                
                if next_trough:
                    # 检查跌幅（从峰顶到谷底的下跌幅度）
                    fall_pct = (current['value'] - next_trough['value']) / current['value']
                    if fall_pct >= self.min_fall_pct:
                        filtered.append(current)
                    else:
                        # 跌幅不足，跳过这个波峰，但保留波谷继续检查
                        pass
                else:
                    filtered.append(current)
            
            i += 1
        
        # 重新整理：确保波谷和波峰交替出现
        if len(filtered) < 2:
            return filtered
        
        # 确保第一个是波谷
        final_filtered = []
        for e in filtered:
            if not final_filtered:
                if e['type'] == 'trough':
                    final_filtered.append(e)
            else:
                # 确保交替：波谷后是波峰，波峰后是波谷
                if final_filtered[-1]['type'] != e['type']:
                    final_filtered.append(e)
        
        return final_filtered
    
    def run(self, prices):
        """完整流程：平滑 + 找极值点 + 过滤"""
        smoothed = self.smooth(prices)
        extremums = self.find_true_peaks_troughs(prices, smoothed.values)
        extremums = self.filter_by_rise_fall_pct(extremums, prices)
        return smoothed, extremums
    
    def print_result(self, extremums, dates=None):
        """打印分析结果"""
        print("=" * 80)
        print(f"平滑窗口: {self.ma_window}天 | 搜索窗口: 前后各{self.search_window}天")
        print(f"最小涨幅: {self.min_rise_pct*100}% (波谷→波峰) | 最小跌幅: {self.min_fall_pct*100}% (波峰→波谷)")
        print("=" * 80)
        
        if not extremums:
            print("未找到任何显著波峰波谷")
            return
        
        peaks = [e for e in extremums if e['type'] == 'peak']
        troughs = [e for e in extremums if e['type'] == 'trough']
        
        print(f"共找到 {len(extremums)} 个极值点（波峰{len(peaks)}个，波谷{len(troughs)}个）")
        print("-" * 80)
        
        for e in extremums:
            type_str = "波峰▲" if e['type'] == 'peak' else "波谷▼"
            date_str = f" 日期:{dates[e['index']]}" if dates and e['index'] < len(dates) else ""
            print(f"  {type_str} 位置[{e['index']}]{date_str} 净值:{e['value']:.4f}")
        print("=" * 80)
    
    def export_extremums_to_csv(self, extremums, dates, filename="extremums.csv"):
        """导出极值点到CSV文件"""
        if not extremums:
            print("没有极值点可导出")
            return None
        
        data = []
        for e in extremums:
            data.append({
                '类型': '波峰' if e['type'] == 'peak' else '波谷',
                '日期': dates[e['index']] if dates and e['index'] < len(dates) else '',
                '净值': e['value']
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"极值点已导出到 {filename}")
        return df
    
    def get_trading_signals(self, extremums, dates=None):
        """
        生成交易信号（买入/卖出点）
        返回: 买入点（波谷）和卖出点（波峰）的配对列表
        """
        signals = []
        
        for i in range(len(extremums) - 1):
            curr = extremums[i]
            next_e = extremums[i + 1]
            
            if curr['type'] == 'trough' and next_e['type'] == 'peak':
                rise_pct = (next_e['value'] - curr['value']) / curr['value'] * 100
                
                signal = {
                    '买入日期': dates[curr['index']] if dates else curr['index'],
                    '买入净值': curr['value'],
                    '卖出日期': dates[next_e['index']] if dates else next_e['index'],
                    '卖出净值': next_e['value'],
                    '涨幅(%)': round(rise_pct, 2),
                    '持有天数': next_e['index'] - curr['index']
                }
                signals.append(signal)
        
        return signals
    
    def check_sell_trigger(self, extremums, raw_prices, dates=None, current_idx=None):
        """
        检查是否触发卖出条件（从最近波峰回调超过 min_fall_pct）
        """
        if current_idx is None:
            current_idx = len(raw_prices) - 1
        
        # 找最近的波峰
        recent_peaks = [e for e in extremums if e['type'] == 'peak' and e['index'] <= current_idx]
        if not recent_peaks:
            return None
        
        last_peak = recent_peaks[-1]
        current_price = raw_prices[current_idx]
        
        fall_pct = (last_peak['value'] - current_price) / last_peak['value']
        
        if fall_pct >= self.min_fall_pct:
            return {
                '峰值日期': dates[last_peak['index']] if dates else last_peak['index'],
                '峰值净值': last_peak['value'],
                '当前日期': dates[current_idx] if dates else current_idx,
                '当前净值': current_price,
                '回调幅度(%)': round(fall_pct * 100, 2),
                '触发卖出': True
            }
        
        return None
    
    def get_statistics(self, extremums, raw_prices):
        """获取统计信息"""
        if not extremums:
            return {
                'total_extremums': 0,
                'peak_count': 0,
                'trough_count': 0,
                'avg_rise': 0,
                'max_rise': 0,
                'avg_fall': 0,
                'max_fall': 0
            }
        
        peaks = [e for e in extremums if e['type'] == 'peak']
        troughs = [e for e in extremums if e['type'] == 'trough']
        
        # 计算涨幅统计
        rises = []
        falls = []
        for i in range(len(extremums) - 1):
            curr = extremums[i]
            next_e = extremums[i + 1]
            if curr['type'] == 'trough' and next_e['type'] == 'peak':
                rise = (next_e['value'] - curr['value']) / curr['value'] * 100
                rises.append(rise)
            elif curr['type'] == 'peak' and next_e['type'] == 'trough':
                fall = (curr['value'] - next_e['value']) / curr['value'] * 100
                falls.append(fall)
        
        return {
            'total_extremums': len(extremums),
            'peak_count': len(peaks),
            'trough_count': len(troughs),
            'avg_rise': np.mean(rises) if rises else 0,
            'max_rise': np.max(rises) if rises else 0,
            'avg_fall': np.mean(falls) if falls else 0,
            'max_fall': np.max(falls) if falls else 0
        }


# 数据加载函数
def load_fund_data(csv_path):
    """读取基金净值CSV文件"""
    df = pd.read_csv(csv_path)
    
    print("CSV文件列名:", df.columns.tolist())
    
    # 找到净值的列名
    nav_col = None
    for col in ['单位净值', '净值', 'nav', 'NAV']:
        if col in df.columns:
            nav_col = col
            break
    
    if nav_col is None:
        nav_col = df.columns[2]
    
    # 找到日期的列名
    date_col = None
    for col in ['日期', 'date', 'Date', 'DATE']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        date_col = df.columns[1]
    
    dates = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d').tolist()
    prices = df[nav_col].values
    
    # 反转数据（如果日期是从新到旧）
    if len(dates) > 1:
        first_date = pd.to_datetime(dates[0])
        last_date = pd.to_datetime(dates[-1])
        if first_date > last_date:
            dates = dates[::-1]
            prices = prices[::-1]
    
    print(f"数据加载成功：{len(prices)} 条记录")
    print(f"日期范围：{dates[0]} 至 {dates[-1]}")
    print(f"净值范围：{prices.min():.4f} - {prices.max():.4f}")
    
    return dates, prices


# 测试算法模块
if __name__ == "__main__":
    # 生成模拟数据测试
    np.random.seed(42)
    days = 200
    dates = pd.date_range('2024-01-01', periods=days).strftime('%Y-%m-%d').tolist()
    prices = 1.0 + np.cumsum(np.random.randn(days) * 0.01)
    prices = np.maximum(prices, 0.8)
    
    finder = MovingAveragePeakTroughFinder(
        ma_window=7,
        prominence_pct=0.02,
        min_distance=7,
        min_rise_pct=0.10,
        min_fall_pct=0.04,
        search_window=3
    )
    
    smoothed, extremums = finder.run(prices)
    finder.print_result(extremums, dates)
    
    signals = finder.get_trading_signals(extremums, dates)
    if signals:
        print("\n交易信号:")
        for s in signals:
            print(f"  {s}")