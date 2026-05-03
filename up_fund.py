"""
基金净值更新脚本
功能：从efinance获取最新净值，更新到CSV文件的单位净值和累计净值列
"""

import pandas as pd
import efinance as ef
from datetime import datetime
import os


def get_latest_nav(fund_code):
    """
    获取基金最新净值
    
    参数:
        fund_code: 基金代码
    
    返回:
        (latest_nav, latest_date): 最新净值和日期
    """
    try:
      
        # 指定基金
        fund_info = ef.fund.get_realtime_increase_rate(fund_code)
        
        if fund_info.empty:
            print(f"未找到基金 {fund_code}")
            return None, None
        
        row = fund_info.iloc[0]
        latest_nav = row['最新净值']
        latest_date = row['最新净值公开日期']
        
        # 如果日期为空，使用今天日期
        if pd.isna(latest_date) or latest_date is None:
            latest_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"获取成功: {fund_code} 最新净值 {latest_nav} 日期 {latest_date}")
        return latest_nav, latest_date
        
    except Exception as e:
        print(f"获取基金数据失败: {e}")
        return None, None


def update_fund_csv(fund_code, csv_file):
    """
    更新基金CSV文件
    
    参数:
        fund_code: 基金代码
        csv_file: CSV文件路径
    """
    # 1. 获取最新净值
    latest_nav, latest_date = get_latest_nav(fund_code)
    
    if latest_nav is None:
        print("无法获取最新净值，操作中止")
        return False
    
    # 2. 检查CSV文件是否存在
    if os.path.exists(csv_file):
        # 读取现有CSV
        df = pd.read_csv(csv_file)
        print(f"读取现有文件: {csv_file}, 共{len(df)}条记录")
        
        # 检查是否已存在该日期的数据
        if latest_date in df['日期'].values:
            # 更新现有记录
            idx = df[df['日期'] == latest_date].index[0]
            df.loc[idx, '单位净值'] = latest_nav
            df.loc[idx, '累计净值'] = latest_nav
            # 涨跌幅保持原值（不修改）
            print(f"更新 {latest_date} 的净值: {latest_nav}")
        else:
            # 新增记录（插入到第一行）
            new_row = pd.DataFrame({
                '日期': [latest_date],
                '单位净值': [latest_nav],
                '累计净值': [latest_nav],
                '涨跌幅': [None]  # 涨跌幅留空
            })
            df = pd.concat([new_row, df], ignore_index=True)
            print(f"新增 {latest_date} 的净值: {latest_nav}")
    else:
        # 文件不存在，创建新文件
        df = pd.DataFrame({
            '日期': [latest_date],
            '单位净值': [latest_nav],
            '累计净值': [latest_nav],
            '涨跌幅': [None]
        })
        print(f"创建新文件: {csv_file}")
    
    # 3. 保存CSV
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"保存成功: {csv_file}")
    print(f"最新数据: {latest_date} 单位净值={latest_nav}, 累计净值={latest_nav}")
    
    return True


# 主程序
if __name__ == "__main__":
    fund_codes = ['011840', '013180', '015599']
    for fund_code in fund_codes:
        # 配置
        csv_file = rf"{fund_code}.csv"
        
        # 执行更新
        update_fund_csv(fund_code, csv_file)