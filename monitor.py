import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='etf_monitor.log')

# ETF 监控列表
ETFS = {
    "159501": "纳指ETF",
    "513500": "半导体ETF"
}

# 邮件配置 (从环境变量获取)
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'kerry@mails.dev')
MAIL_API_KEY = os.getenv('MAIL_API_KEY', 'default_api_key') # 替换为你的 mails.dev API Key
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', 'yangzhi72@126.com')
MAIL_SERVER = 'smtp.mails.dev' # mails.dev 的 SMTP 地址
MAIL_PORT = 587 # mails.dev 的 SMTP 端口

def fetch_etf_data(etf_code):
    """
    从 wise-etf.com 爬取 ETF 数据
    """
    url = f"https://www.wise-etf.com/etf/{etf_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 如果请求失败，抛出 HTTPError
        soup = BeautifulSoup(response.text, 'lxml')

        # 查找溢价率
        premium_rate_tag = soup.find('div', string='溢价率')
        if premium_rate_tag:
            premium_rate_value = premium_rate_tag.find_next_sibling('div').text.strip()
            logging.info(f"成功获取 ETF {etf_code} 溢价率: {premium_rate_value}")
            return premium_rate_value
        else:
            logging.warning(f"未找到 ETF {etf_code} 的溢价率")
            return "N/A"
    except requests.exceptions.RequestException as e:
        logging.error(f"爬取 ETF {etf_code} 数据失败: {e}")
        return None
    except Exception as e:
        logging.error(f"解析 ETF {etf_code} 数据失败: {e}")
        return None

def send_email(subject, body):
    """
    使用 mails.dev API 发送邮件
    """
    msg = MIMEText(body, 'html', 'utf-8')
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject

    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()  # 启动 TLS 加密
        server.login(SENDER_EMAIL, MAIL_API_KEY)  # 使用邮件地址和 API Key 登录
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        logging.info(f"邮件发送成功: '{subject}'")
    except smtplib.SMTPAuthenticationError:
        logging.error("邮件发送失败: 认证失败, 请检查 SENDER_EMAIL 和 MAIL_API_KEY。")
    except smtplib.SMTPConnectError as e:
        logging.error(f"邮件发送失败: 无法连接到 SMTP 服务器 {MAIL_SERVER}:{MAIL_PORT} - {e}")
    except Exception as e:
        logging.error(f"邮件发送失败: {e}")

def monitor_etfs():
    """
    监控 ETF 并在溢价率低于 3% 时发送通知邮件
    """
    logging.info("开始执行 ETF 监控任务...")
    for code, name in ETFS.items():
        premium = fetch_etf_data(code)
        if premium and premium != "N/A":
            try:
                # 假设溢价率格式为 "X.XX%"
                premium_value = float(premium.replace('%', ''))
                if premium_value < 3.0:
                    subject = f"ETF 监控提醒: {name} ({code}) 溢价率低于 3%"
                    body = f"ETF {name} ({code}) 当前溢价率为: {premium}，请关注！"
                    send_email(subject, body)
                logging.info(f"ETF {name} ({code}) 溢价率: {premium}")
            except ValueError:
                logging.warning(f"无法解析 ETF {name} ({code}) 的溢价率 {premium}。跳过阈值检查。")
        else:
            logging.warning(f"未能获取 ETF {name} ({code}) 的溢价率，跳过通知。")
    logging.info("ETF 监控任务执行完毕。")

def generate_daily_summary():
    """
    生成并发送每日 ETF 数据汇总邮件
    """
    logging.info("开始生成每日 ETF 数据汇总...")
    summary_body = "<h1>每日 ETF 数据汇总</h1><table border='1'><tr><th>ETF 代码</th><th>ETF 名称</th><th>溢价率</th></tr>"
    all_data_fetched = True
    for code, name in ETFS.items():
        premium = fetch_etf_data(code)
        if premium:
            summary_body += f"<tr><td>{code}</td><td>{name}</td><td>{premium}</td></tr>"
        else:
            summary_body += f"<tr><td>{code}</td><td>{name}</td><td>获取失败</td></tr>"
            all_data_fetched = False
    summary_body += "</table>"

    subject = f"ETF 每日数据汇总 - {datetime.now().strftime('%Y-%m-%d')}"
    send_email(subject, summary_body)
    logging.info("每日 ETF 数据汇总邮件发送完毕。")

if __name__ == "__main__":
    # 根据命令行参数判断执行哪种任务
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "summary":
        generate_daily_summary()
    else:
        monitor_etfs()
