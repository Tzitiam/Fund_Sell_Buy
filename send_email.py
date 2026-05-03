"""
邮件自动发送脚本
用于发送每日自动报告（HTML格式，手机友好）
包含基金分析报告和百分位数据
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from fund_analysis import BatchFundAnalyzer
from percentile_simple import PercentileAnalyzer

# ========== 配置日志 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ========== 加载配置 ==========
load_dotenv()


def get_percentile_data(fund_codes):
    """获取所有基金的百分位数据"""
    percentile_data = {}
    for code in fund_codes:
        try:
            analyzer = PercentileAnalyzer(f"{code}.csv")
            pct = analyzer.get_current_percentile()
            if pct is not None:
                percentile_data[code] = pct
            else:
                percentile_data[code] = None
        except Exception as e:
            logger.warning(f"获取{code}百分位失败: {e}")
            percentile_data[code] = None
    return percentile_data


def get_html_report():
    """
    执行基金分析并生成HTML报告（包含百分位）
    """
    logger.info("开始执行基金分析...")
    
    # 要分析的基金代码
    fund_codes = ['011840', '013180', '015599']
    
    # 获取百分位数据
    percentile_data = get_percentile_data(fund_codes)
    logger.info(f"百分位数据: {percentile_data}")
    
    # 创建分析器
    analyzer = BatchFundAnalyzer()
    
    # 执行分析
    analyzer.analyze_multiple_funds(fund_codes)
    
    # 生成HTML报告（传入百分位数据）
    html_content = analyzer.generate_html_report(percentile_data)
    
    logger.info("基金分析完成，HTML报告已生成")
    
    return html_content


def send_html_email(subject, html_content, recipients):
    """
    发送HTML格式的邮件
    
    参数:
        subject: 邮件主题
        html_content: HTML邮件内容
        recipients: 收件人列表
    """
    # 邮件配置
    smtp_server = os.getenv("EMAIL_SERVER")
    smtp_port = int(os.getenv("EMAIL_PORT"))
    sender_email = os.getenv("EMAIL_ADDR")
    sender_password = os.getenv("EMAIL_PWD")
    
    # 创建邮件
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    
    # 纯文本备用内容
    text_content = "请使用支持HTML的邮件客户端查看本邮件，或打开附件中的HTML文件。"
    
    # 添加纯文本和HTML版本
    part_text = MIMEText(text_content, 'plain', 'utf-8')
    part_html = MIMEText(html_content, 'html', 'utf-8')
    
    msg.attach(part_text)
    msg.attach(part_html)
    
    # 发送邮件
    try:
        # 根据端口选择SSL或TLS
        if smtp_port == 465:
            # SSL方式
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # TLS方式
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        
        logger.info(f"邮件发送成功！收件人: {recipients}")
        return True
        
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        raise


def send_report():
    """发送HTML格式的分析报告邮件"""
    try:
        # 获取HTML报告
        html_content = get_html_report()
        
        # 邮件信息
        now = datetime.now()
        email_subject = f"【基金分析日报】{now.strftime('%Y-%m-%d')}"
        recipients = [os.getenv("SEND_EMAIL")]
        
        # 发送邮件
        send_html_email(email_subject, html_content, recipients)
        
        logger.info("报告发送完成！")
        
    except Exception as e:
        logger.error(f"报告发送失败: {e}")
        raise


if __name__ == "__main__":
    send_report()