class FundParameterConfig:
    """
    基金参数配置管理类
    支持为每只基金独立设置参数，并可保存/加载配置
    """
    
    # 默认参数模板
    DEFAULT_PARAMS = {
        'ma_window': 2,           # 移动平均窗口
        'prominence_pct': 2.0,    # 显著性阈值 (%)
        'min_distance': 7,        # 最小间距（天）
        'min_rise_pct': 10.0,     # 最小涨幅 (%)
        'min_fall_pct': 4.0,      # 最小跌幅 (%)
        'search_window': 3        # 搜索窗口（天）
    }
    
    # 基金类型参数模板
    FUND_TYPE_TEMPLATES = {
        '015599': {
            'ma_window': 2,
            'prominence_pct': 2.0,
            'min_distance': 7,
            'min_rise_pct': 10.0,
            'min_fall_pct': 4.0,
            'search_window': 3,
            'description': '国证航天军工'
        },
        '013180': {
            'ma_window': 2,
            'prominence_pct': 2.0,
            'min_distance': 7,
            'min_rise_pct': 5.0,
            'min_fall_pct': 4.0,
            'search_window': 3,
            'description': '新能源电池'
        },
        '011840': {
            'ma_window': 2,
            'prominence_pct': 2.0,
            'min_distance': 7,
            'min_rise_pct': 10.0,
            'min_fall_pct': 4.0,
            'search_window': 3,
            'description': '人工智能'
        }
    }