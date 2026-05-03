"""
简单定时任务模块（日志轮转版）
功能：先执行 up_fund.py，等待15秒，再执行 send_email.py
日志自动轮转，保留最近7天
"""

import subprocess
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os
import sys

# ========== 配置日志（自动轮转） ==========
def setup_rotating_logger():
    """配置带轮转的日志，同时输出到控制台和文件"""
    
    # 创建logs目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志文件路径
    log_filename = os.path.join(log_dir, "scheduler.log")
    
    # 创建日志器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（轮转：每个文件最大10MB，保留7个备份）
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,           # 保留7个备份
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


logger = setup_rotating_logger()


def run_script(script_name):
    """运行Python脚本"""
    logger.info(f"开始执行: {script_name}")
    start_time = datetime.now()
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, script_name)
        
        if not os.path.exists(script_path):
            logger.error(f"脚本不存在: {script_path}")
            return False
        
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    logger.info(f"[{script_name}] {line}")
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line:
                    logger.warning(f"[{script_name}] {line}")
        
        if result.returncode == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"{script_name} 执行成功，耗时 {elapsed:.2f} 秒")
            return True
        else:
            logger.error(f"{script_name} 执行失败，返回码: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"{script_name} 执行超时（5分钟）")
        return False
    except Exception as e:
        logger.error(f"{script_name} 执行异常: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("定时任务开始")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 步骤1：更新基金净值
    logger.info("步骤1: 更新基金净值...")
    success_up = run_script("up_fund.py")
    
    if not success_up:
        logger.error("基金净值更新失败，终止任务")
        return
    
    # 等待15秒
    logger.info("等待15秒，确保数据写入完成...")
    for i in range(15, 0, -1):
        if i % 5 == 0 or i <= 3:
            logger.info(f"等待中... {i}秒")
        time.sleep(1)
    logger.info("等待完成，继续执行")
    
    # 步骤2：发送邮件报告
    logger.info("步骤2: 发送邮件报告...")
    success_email = run_script("send_email.py")
    
    if success_email:
        logger.info("=" * 60)
        logger.info("定时任务完成")
        logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
    else:
        logger.error("邮件发送失败，定时任务未完成")


if __name__ == "__main__":
    main()