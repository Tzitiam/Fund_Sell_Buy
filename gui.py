"""
基金可视化模块
功能：提供交互式可视化界面，支持参数调节
"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import numpy as np
from model import MovingAveragePeakTroughFinder, load_fund_data
# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

class FundVisualizer:
    """基金可视化类"""
    
    def __init__(self, prices, dates=None, finder=None):
        """
        初始化可视化器
        
        参数:
            prices: 净值数据
            dates: 日期数据
            finder: MovingAveragePeakTroughFinder实例（可选）
        """
        self.prices = np.array(prices)
        self.dates = dates
        self.finder = finder if finder else MovingAveragePeakTroughFinder()
        self.fig = None
        self.ax = None
    
    def update(self, ma_window, prominence_pct, min_distance, 
               min_rise_pct, min_fall_pct, search_window):
        """更新参数并重绘图表"""
        # 更新分析器参数
        self.finder.ma_window = int(ma_window)
        self.finder.prominence_pct = prominence_pct / 100
        self.finder.min_distance = int(min_distance)
        self.finder.min_rise_pct = min_rise_pct / 100
        self.finder.min_fall_pct = min_fall_pct / 100
        self.finder.search_window = int(search_window)
        
        # 执行分析
        smoothed, extremums = self.finder.run(self.prices)
        
        # 清空并重绘
        self.ax.clear()
        
        # 绘制原始净值
        self.ax.plot(self.prices, 'b-', label='原始净值', alpha=0.7, linewidth=0.8)
        
        # 绘制平滑曲线
        self.ax.plot(smoothed, 'r-', label=f'平滑曲线(窗口={self.finder.ma_window})', 
                    linewidth=1.5, alpha=0.4)
        
        # 标记极值点
        for e in extremums:
            if e['type'] == 'peak':
                self.ax.scatter(e['index'], e['value'], color='green', s=100, 
                              marker='^', zorder=5, alpha=0.9)
                if self.dates and e['index'] < len(self.dates):
                    date_str = self.dates[e['index']][5:]  # 只显示月-日
                    self.ax.annotate(f'{e["value"]:.3f}\n{date_str}', 
                                    (e['index'], e['value']),
                                    textcoords="offset points", xytext=(0, 10),
                                    ha='center', fontsize=7, color='green', fontweight='bold')
            else:
                self.ax.scatter(e['index'], e['value'], color='orange', s=100, 
                              marker='v', zorder=5, alpha=0.9)
                if self.dates and e['index'] < len(self.dates):
                    date_str = self.dates[e['index']][5:]
                    self.ax.annotate(f'{e["value"]:.3f}\n{date_str}', 
                                    (e['index'], e['value']),
                                    textcoords="offset points", xytext=(0, -15),
                                    ha='center', fontsize=7, color='orange', fontweight='bold')
        
        # 连接涨跌段
        for i in range(len(extremums) - 1):
            curr = extremums[i]
            next_e = extremums[i + 1]
            
            if curr['type'] == 'trough' and next_e['type'] == 'peak':
                rise_pct = (next_e['value'] - curr['value']) / curr['value'] * 100
                self.ax.plot([curr['index'], next_e['index']], 
                           [curr['value'], next_e['value']], 
                           'g--', alpha=0.6, linewidth=1)
                mid_x = (curr['index'] + next_e['index']) / 2
                mid_y = (curr['value'] + next_e['value']) / 2
                self.ax.annotate(f'+{rise_pct:.1f}%', 
                                (mid_x, mid_y), fontsize=8, color='darkgreen', 
                                ha='center', alpha=0.8)
            
            elif curr['type'] == 'peak' and next_e['type'] == 'trough':
                fall_pct = (curr['value'] - next_e['value']) / curr['value'] * 100
                self.ax.plot([curr['index'], next_e['index']], 
                           [curr['value'], next_e['value']], 
                           'r--', alpha=0.6, linewidth=1)
                mid_x = (curr['index'] + next_e['index']) / 2
                mid_y = (curr['value'] + next_e['value']) / 2
                self.ax.annotate(f'-{fall_pct:.1f}%', 
                                (mid_x, mid_y), fontsize=8, color='darkred', 
                                ha='center', alpha=0.8)
        
        # 设置x轴标签
        if self.dates is not None and len(self.dates) == len(self.prices):
            step = max(1, len(self.dates) // 15)
            tick_positions = list(range(0, len(self.dates), step))
            tick_labels = [self.dates[i] for i in tick_positions]
            self.ax.set_xticks(tick_positions)
            self.ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        
        # 设置标题和标签
        self.ax.set_title('基金净值波峰波谷识别', fontsize=14)
        self.ax.set_xlabel('日期')
        self.ax.set_ylabel('单位净值')
        self.ax.legend(loc='upper left')
        self.ax.grid(True, alpha=0.3)
        
        # 显示统计信息
        peaks = [e for e in extremums if e['type'] == 'peak']
        troughs = [e for e in extremums if e['type'] == 'trough']
        signals = self.finder.get_trading_signals(extremums, self.dates)
        
        info_text = f'波峰: {len(peaks)}个 | 波谷: {len(troughs)}个 | 交易信号: {len(signals)}个\n'
        info_text += f'涨幅阈值: {self.finder.min_rise_pct*100:.0f}% | 跌幅阈值: {self.finder.min_fall_pct*100:.0f}%'
        
        self.ax.text(0.02, 0.98, info_text, transform=self.ax.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        
        self.fig.canvas.draw_idle()
        
        # 控制台打印结果
        print("\n" + "=" * 80)
        print("【当前参数下的极值点】")
        print("=" * 80)
        self.finder.print_result(extremums, self.dates)
        
        if signals:
            print("\n【交易信号（买入→卖出配对）】")
            print("-" * 80)
            for sig in signals:
                print(f"  买入: {sig['买入日期']} @ {sig['买入净值']:.4f} → "
                      f"卖出: {sig['卖出日期']} @ {sig['卖出净值']:.4f} | "
                      f"涨幅: {sig['涨幅(%)']}% | 持有: {sig['持有天数']}天")
            print("=" * 80)
        
        # 检查卖出触发
        sell_trigger = self.finder.check_sell_trigger(extremums, self.prices, self.dates)
        if sell_trigger and sell_trigger['触发卖出']:
            print("\n" + "!" * 80)
            print("【卖出触发警告】")
            print(f"  从峰值 {sell_trigger['峰值日期']} @ {sell_trigger['峰值净值']:.4f}")
            print(f"  已回调 {sell_trigger['回调幅度(%)']}%，当前净值 {sell_trigger['当前净值']:.4f}")
            print(f"  建议卖出！")
            print("!" * 80)
        
        return extremums
    
    def show(self):
        """显示交互式界面"""
        self.fig, self.ax = plt.subplots(figsize=(16, 9))
        plt.subplots_adjust(bottom=0.35)
        
        # 初始绘图
        self.update(
            self.finder.ma_window,
            self.finder.prominence_pct * 100,
            self.finder.min_distance,
            self.finder.min_rise_pct * 100,
            self.finder.min_fall_pct * 100,
            self.finder.search_window
        )
        
        # 创建滑动条
        ax_ma = plt.axes([0.15, 0.28, 0.7, 0.03])
        ax_prominence = plt.axes([0.15, 0.23, 0.7, 0.03])
        ax_distance = plt.axes([0.15, 0.18, 0.7, 0.03])
        ax_rise = plt.axes([0.15, 0.13, 0.7, 0.03])
        ax_fall = plt.axes([0.15, 0.08, 0.7, 0.03])
        ax_search = plt.axes([0.15, 0.03, 0.7, 0.03])
        
        ma_slider = Slider(ax_ma, '平滑窗口', 2, 30, 
                          valinit=self.finder.ma_window, valstep=1)
        prominence_slider = Slider(ax_prominence, '显著性阈值 (%)', 0.5, 8.0, 
                                  valinit=self.finder.prominence_pct*100, valstep=0.1)
        distance_slider = Slider(ax_distance, '最小间距（天）', 2, 30, 
                                valinit=self.finder.min_distance, valstep=1)
        rise_slider = Slider(ax_rise, '最小涨幅 (%)', 5.0, 25.0, 
                            valinit=self.finder.min_rise_pct*100, valstep=0.5)
        fall_slider = Slider(ax_fall, '最小跌幅 (%)', 2.0, 10.0, 
                            valinit=self.finder.min_fall_pct*100, valstep=0.5)
        search_slider = Slider(ax_search, '搜索窗口（天）', 1, 10, 
                              valinit=self.finder.search_window, valstep=1)
        
        def update_func(val):
            self.update(ma_slider.val, prominence_slider.val, distance_slider.val,
                       rise_slider.val, fall_slider.val, search_slider.val)
        
        ma_slider.on_changed(update_func)
        prominence_slider.on_changed(update_func)
        distance_slider.on_changed(update_func)
        rise_slider.on_changed(update_func)
        fall_slider.on_changed(update_func)
        search_slider.on_changed(update_func)
        
        plt.show()


# 主程序入口
if __name__ == "__main__":
    import sys
    import os
    
    # 默认CSV文件
    csv_file = "011840.csv"
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    try:
        dates, prices = load_fund_data(csv_file)
    except FileNotFoundError:
        print(f"文件 {csv_file} 未找到")
        print(f"当前目录: {os.getcwd()}")
        print("请确保CSV文件在当前目录下，或通过命令行指定文件路径:")
        print("  python fund_visualizer.py your_fund.csv")
        exit(1)
    
    # 创建分析器
    finder = MovingAveragePeakTroughFinder(
        ma_window=7,           # 平滑窗口
        prominence_pct=0.02,   # 显著性阈值
        min_distance=7,        # 最小间距
        min_rise_pct=0.10,     # 最小涨幅10%
        min_fall_pct=0.04,     # 最小跌幅4%
        search_window=3        # 搜索窗口
    )
    
    # 先执行一次分析并导出结果
    smoothed, extremums = finder.run(prices)
    finder.print_result(extremums, dates)
    finder.export_extremums_to_csv(extremums, dates, "fund_extremums.csv")
    
    # 启动可视化界面
    print("\n启动可视化界面...")
    visualizer = FundVisualizer(prices, dates, finder)
    visualizer.show()