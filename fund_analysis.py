"""
批量基金分析模块
功能：循环分析多只基金，输出极值点信息，判断交易信号，并生成HTML报告
"""

import pandas as pd
import numpy as np
from datetime import datetime
from model import MovingAveragePeakTroughFinder, load_fund_data
from size import FundParameterConfig


class BatchFundAnalyzer:
    """
    批量基金分析器
    支持根据基金代码循环分析多只基金
    """
    
    def __init__(self):
        """初始化批量分析器"""
        self.config = FundParameterConfig()
        self.results = {}  # 存储每只基金的分析结果
        self.sell_signals = []  # 存储卖出信号
    
    def get_fund_file_path(self, fund_code):
        """根据基金代码获取CSV文件路径"""
        return f"{fund_code}.csv"
    
    def analyze_single_fund(self, fund_code, override_params=None):
        """分析单只基金"""
        print(f"\n正在分析基金: {fund_code}")
        
        # 获取基金参数
        if override_params:
            params = override_params
        else:
            fund_config = self.config.FUND_TYPE_TEMPLATES.get(fund_code, {})
            if fund_config:
                params = {
                    'ma_window': fund_config.get('ma_window', self.config.DEFAULT_PARAMS['ma_window']),
                    'prominence_pct': fund_config.get('prominence_pct', self.config.DEFAULT_PARAMS['prominence_pct']) / 100,
                    'min_distance': fund_config.get('min_distance', self.config.DEFAULT_PARAMS['min_distance']),
                    'min_rise_pct': fund_config.get('min_rise_pct', self.config.DEFAULT_PARAMS['min_rise_pct']) / 100,
                    'min_fall_pct': fund_config.get('min_fall_pct', self.config.DEFAULT_PARAMS['min_fall_pct']) / 100,
                    'search_window': fund_config.get('search_window', self.config.DEFAULT_PARAMS['search_window'])
                }
                desc = fund_config.get('description', '')
            else:
                params = {
                    'ma_window': self.config.DEFAULT_PARAMS['ma_window'],
                    'prominence_pct': self.config.DEFAULT_PARAMS['prominence_pct'] / 100,
                    'min_distance': self.config.DEFAULT_PARAMS['min_distance'],
                    'min_rise_pct': self.config.DEFAULT_PARAMS['min_rise_pct'] / 100,
                    'min_fall_pct': self.config.DEFAULT_PARAMS['min_fall_pct'] / 100,
                    'search_window': self.config.DEFAULT_PARAMS['search_window']
                }
                desc = ''
        
        # 加载数据
        file_path = self.get_fund_file_path(fund_code)
        try:
            dates, prices = load_fund_data(file_path)
        except FileNotFoundError:
            print(f"错误: 找不到文件 {file_path}")
            return None
        
        # 创建分析器并执行分析
        finder = MovingAveragePeakTroughFinder(**params)
        smoothed, extremums = finder.run(prices)
        
        # 计算额外的涨跌幅数据
        latest_price = prices[-1]
        latest_date = dates[-1]
        
        # 计算倒一和倒二的涨跌幅
        last_to_second_pct = None
        latest_to_last_pct = None
        last_peak_value = None
        second_last_trough_value = None
        
        if len(extremums) >= 2:
            last_extremum = extremums[-1]
            second_last_extremum = extremums[-2]
            
            if last_extremum['type'] == 'peak' and second_last_extremum['type'] == 'trough':
                last_peak_value = last_extremum['value']
                second_last_trough_value = second_last_extremum['value']
                # 倒数第一个峰值相对于倒数第二个谷值的涨幅
                last_to_second_pct = (last_peak_value - second_last_trough_value) / second_last_trough_value * 100
                # 最新净值相对于倒数第一个峰值的回调幅度
                latest_to_last_pct = (last_peak_value - latest_price) / last_peak_value * 100
        
        # 存储结果
        result = {
            'fund_code': fund_code,
            'description': desc,
            'dates': dates,
            'prices': prices,
            'extremums': extremums,
            'finder': finder,
            'params': params,
            'latest_price': latest_price,
            'latest_date': latest_date,
            'last_to_second_pct': last_to_second_pct,  # 倒一峰值相对于倒二谷值的涨幅
            'latest_to_last_pct': latest_to_last_pct,  # 最新净值相对于倒一峰值的回调
            'last_peak_value': last_peak_value,
            'second_last_trough_value': second_last_trough_value
        }
        
        self.results[fund_code] = result
        
        # 判断交易状态
        signal = self.check_trading_status(result)
        if signal:
            self.sell_signals.append(signal)
        
        return result
    
    def check_trading_status(self, result):
        """
        判断基金的交易状态
        
        三个条件：
        1. 倒数第一个极值点是波峰，倒数第二个极值点是波谷
        2. 倒数第一个和倒数第二个的数值相差 >= min_rise_pct
        3. 最新净值与倒数第一个波峰的回调幅度 >= min_fall_pct
        """
        extremums = result['extremums']
        dates = result['dates']
        fund_code = result['fund_code']
        latest_price = result['latest_price']
        min_rise_pct = result['params']['min_rise_pct'] * 100
        min_fall_pct = result['params']['min_fall_pct'] * 100
        
        if len(extremums) < 2:
            return None
        
        last_extremum = extremums[-1]
        second_last_extremum = extremums[-2]
        
        # 条件1
        condition1 = (last_extremum['type'] == 'peak' and second_last_extremum['type'] == 'trough')
        if not condition1:
            return None
        
        # 条件2
        trough_value = second_last_extremum['value']
        peak_value = last_extremum['value']
        rise_pct = (peak_value - trough_value) / trough_value * 100
        condition2 = rise_pct >= min_rise_pct
        if not condition2:
            return None
        
        # 条件3
        fall_pct = (peak_value - latest_price) / peak_value * 100
        condition3 = fall_pct >= min_fall_pct
        if not condition3:
            return None
        
        return {
            'fund_code': fund_code,
            'fund_name': result.get('description', ''),
            'buy_date': dates[second_last_extremum['index']],
            'buy_price': trough_value,
            'sell_date': dates[last_extremum['index']],
            'sell_price': peak_value,
            'rise_pct': round(rise_pct, 2),
            'current_date': result['latest_date'],
            'current_price': latest_price,
            'fall_pct': round(fall_pct, 2)
        }
    
    def analyze_multiple_funds(self, fund_codes):
        """批量分析多只基金"""
        print("\n批量基金分析开始")
        print(f"待分析基金: {', '.join(fund_codes)}")
        print("-" * 50)
        
        for fund_code in fund_codes:
            self.analyze_single_fund(fund_code)
        
        return self.results, self.sell_signals
    
    def generate_html_report(self, percentile_data=None):
        """生成手机友好的HTML报告（包含百分位）"""
        now = datetime.now()
        
        # 计算统计信息
        total_funds = len(self.results)
        total_signals = len(self.sell_signals)
        
        # 如果没有传入percentile_data，尝试获取
        if percentile_data is None:
            percentile_data = {}
            try:
                from percentile_simple import PercentileAnalyzer
                for code in self.results.keys():
                    try:
                        analyzer = PercentileAnalyzer(f"{code}.csv")
                        pct = analyzer.get_current_percentile()
                        if pct is not None:
                            percentile_data[code] = pct
                        else:
                            percentile_data[code] = None
                    except:
                        percentile_data[code] = None
            except:
                pass
        
        html = f'''<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <title>基金分析报告</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #f5f7fa;
                padding: 16px;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 20px;
                padding: 20px;
                margin-bottom: 20px;
                color: white;
            }}
            .header h1 {{
                font-size: 22px;
                margin-bottom: 8px;
            }}
            .header .date {{
                font-size: 13px;
                opacity: 0.9;
            }}
            .stats {{
                display: flex;
                justify-content: space-between;
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid rgba(255,255,255,0.2);
            }}
            .stat-item {{
                text-align: center;
                flex: 1;
            }}
            .stat-number {{
                font-size: 28px;
                font-weight: bold;
            }}
            .stat-label {{
                font-size: 12px;
                opacity: 0.8;
                margin-top: 4px;
            }}
            .fund-card {{
                background-color: white;
                border-radius: 16px;
                margin-bottom: 16px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}
            .fund-header {{
                padding: 16px;
                background-color: #f8f9fa;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .fund-code {{
                font-weight: bold;
                font-size: 16px;
                color: #333;
            }}
            .fund-name {{
                font-size: 12px;
                color: #888;
                margin-top: 2px;
            }}
            .fund-content {{
                padding: 16px;
            }}
            .percentile-card {{
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
                text-align: center;
            }}
            .percentile-label {{
                font-size: 12px;
                color: #166534;
                margin-bottom: 4px;
            }}
            .percentile-value {{
                font-size: 28px;
                font-weight: bold;
                color: #166534;
            }}
            .percentile-bar {{
                background-color: #e5e7eb;
                border-radius: 10px;
                height: 8px;
                margin-top: 8px;
                overflow: hidden;
            }}
            .percentile-fill {{
                background: linear-gradient(90deg, #10b981, #3b82f6);
                height: 100%;
                border-radius: 10px;
            }}
            .current-price {{
                background-color: #f0f9ff;
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
                text-align: center;
            }}
            .current-price .label {{
                font-size: 12px;
                color: #666;
            }}
            .current-price .value {{
                font-size: 24px;
                font-weight: bold;
                color: #3b82f6;
            }}
            .current-price .date {{
                font-size: 11px;
                color: #888;
                margin-top: 4px;
            }}
            .key-numbers {{
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
            }}
            .key-number-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
            }}
            .key-number-label {{
                font-size: 13px;
                color: #555;
            }}
            .key-number-value {{
                font-size: 16px;
                font-weight: bold;
            }}
            .key-number-value.up {{
                color: #10b981;
            }}
            .key-number-value.down {{
                color: #dc2626;
            }}
            .threshold-info {{
                font-size: 11px;
                color: #888;
                margin-top: 4px;
            }}
            .extremum-list {{
                margin-top: 12px;
            }}
            .extremum-item {{
                display: flex;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid #f0f0f0;
            }}
            .extremum-icon {{
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                margin-right: 12px;
            }}
            .icon-peak {{
                background-color: #d1fae5;
                color: #10b981;
            }}
            .icon-trough {{
                background-color: #fed7aa;
                color: #f59e0b;
            }}
            .extremum-info {{
                flex: 1;
            }}
            .extremum-date {{
                font-size: 13px;
                font-weight: 500;
            }}
            .extremum-price {{
                font-size: 15px;
                font-weight: bold;
                margin-top: 2px;
            }}
            .extremum-change {{
                font-size: 11px;
                margin-top: 2px;
            }}
            .change-up {{
                color: #10b981;
            }}
            .change-down {{
                color: #dc2626;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                font-size: 11px;
                color: #aaa;
            }}
            hr {{
                margin: 16px 0;
                border: none;
                border-top: 1px solid #eee;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: bold;
                margin: 20px 0 12px 0;
                padding-left: 12px;
                border-left: 4px solid #667eea;
            }}
        </style>
    </head>
    <body>
    <div class="container">
        <div class="header">
            <h1>📊 基金分析报告</h1>
            <div class="date">{now.strftime('%Y年%m月%d日 %H:%M')}</div>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number">{total_funds}</div>
                    <div class="stat-label">分析基金</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{total_signals}</div>
                    <div class="stat-label">卖出信号</div>
                </div>
            </div>
        </div>
        
        <div class="section-title">📋 基金详情</div>
    '''
        
        for code, result in self.results.items():
            extremums = result['extremums']
            dates = result['dates']
            latest_price = result['latest_price']
            latest_date = result['latest_date']
            desc = result.get('description', '')
            
            # 获取百分位（修复：使用局部变量）
            pct_value = percentile_data.get(code, None) if percentile_data else None
            if pct_value is not None:
                percentile_display = f"{pct_value:.2f}%"
                bar_width = pct_value
            else:
                percentile_display = "N/A"
                bar_width = 0
            
            # 获取涨跌幅数据
            last_to_second_pct = result.get('last_to_second_pct')
            latest_to_last_pct = result.get('latest_to_last_pct')
            
            html += f'''
        <div class="fund-card">
            <div class="fund-header">
                <div>
                    <div class="fund-code">{code}</div>
                    <div class="fund-name">{desc}</div>
                </div>
            </div>
            <div class="fund-content">
                <!-- 百分位卡片 -->
                <div class="percentile-card">
                    <div class="percentile-label">📊 历史百分位</div>
                    <div class="percentile-value">{percentile_display}</div>
                    <div class="percentile-bar">
                        <div class="percentile-fill" style="width: {bar_width}%;"></div>
                    </div>
                </div>
                
                <div class="current-price">
                    <div class="label">最新净值</div>
                    <div class="value">{latest_price:.4f}</div>
                    <div class="date">{latest_date}</div>
                </div>
                
                <div class="key-numbers">
                    <div class="key-number-item">
                        <div>
                            <div class="key-number-label">📈 波谷→波峰涨幅</div>
                        </div>
                        <div>
                            <div class="key-number-value {'up' if last_to_second_pct and last_to_second_pct >= 10 else ''}">
                                {f'+{last_to_second_pct:.2f}%' if last_to_second_pct is not None else 'N/A'}
                            </div>
                        </div>
                    </div>
                    <div class="key-number-item">
                        <div>
                            <div class="key-number-label">📉 波峰→当前回调</div>
                        </div>
                        <div>
                            <div class="key-number-value {'down' if latest_to_last_pct and latest_to_last_pct >= 4 else ''}">
                                {f'-{latest_to_last_pct:.2f}%' if latest_to_last_pct is not None else 'N/A'}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div style="font-size: 13px; font-weight: bold; margin-bottom: 8px;">📌 极值点序列</div>
                <div class="extremum-list">
    '''
            
            for idx, e in enumerate(extremums):
                e_type = e['type']
                e_date = dates[e['index']]
                e_value = e['value']
                
                change_text = ""
                change_class = ""
                if idx > 0:
                    prev = extremums[idx-1]
                    if e_type == 'peak' and prev['type'] == 'trough':
                        change = (e_value - prev['value']) / prev['value'] * 100
                        change_text = f"↑ +{change:.1f}%"
                        change_class = "change-up"
                    elif e_type == 'trough' and prev['type'] == 'peak':
                        change = (prev['value'] - e_value) / prev['value'] * 100
                        change_text = f"↓ -{change:.1f}%"
                        change_class = "change-down"
                
                icon = "▲" if e_type == 'peak' else "▼"
                icon_class = "icon-peak" if e_type == 'peak' else "icon-trough"
                
                # 标记最后一个极值点
                is_last_extremum = (idx == len(extremums) - 1)
                suffix = " (当前)" if is_last_extremum else ""
                
                html += f'''
                    <div class="extremum-item">
                        <div class="extremum-icon {icon_class}">{icon}</div>
                        <div class="extremum-info">
                            <div class="extremum-date">{e_date}{suffix}</div>
                            <div class="extremum-price">{e_value:.4f}</div>
                            <div class="extremum-change {change_class}">{change_text}</div>
                        </div>
                    </div>
    '''
            
            html += '''
                </div>
            </div>
        </div>
    '''
        
        html += f'''
        <hr>
        <div class="footer">
            本报告由自动分析系统生成<br>
            仅供参考，不构成投资建议
        </div>
    </div>
    </body>
    </html>
    '''
        
        return html
    
    def save_html_report(self, filename="fund_report.html"):
        """保存HTML报告到文件"""
        html = self.generate_html_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML报告已保存到: {filename}")
        return filename


# 命令行入口
def main():
    """主函数"""
    fund_codes = ['011840', '013180', '015599']
    
    analyzer = BatchFundAnalyzer()
    analyzer.analyze_multiple_funds(fund_codes)
    
    # 生成HTML报告
    html_file = analyzer.save_html_report("fund_report.html")
    
    return analyzer, html_file


if __name__ == "__main__":
    main()