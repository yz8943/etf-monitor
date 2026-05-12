
import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

def get_etf_data(etf_code):
    url = f"https://www.wise-etf.com/etf/{etf_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # 尝试查找溢价率
        premium_rate_element = soup.find('td', text='溢价率：').find_next_sibling('td')
        if premium_rate_element:
            premium_rate_text = premium_rate_element.get_text(strip=True).replace('%', '')
            try:
                premium_rate = float(premium_rate_text)
                return premium_rate
            except ValueError:
                logging.error(f"无法解析ETF {etf_code}的溢价率: {premium_rate_text}")
                return None
        else:
            logging.warning(f"未找到ETF {etf_code}的溢价率信息，尝试查找其他方式。")
            # 备用查找方式 (如果网站结构变化)
            all_tds = soup.find_all('td')
            for i in range(len(all_tds_)):
                if '溢价率' in all_tds[i].text and i + 1 < len(all_tds):
                    premium_rate_text = all_tds[i+1].get_text(strip=True).replace('%', '')
                    try:
                        premium_rate = float(premium_rate_text)
                        return premium_rate
                    except ValueError:
                        logging.error(f"备用查找: 无法解析ETF {etf_code}的溢价率: {premium_rate_text}")
                        return None
            logging.error(f"未能找到ETF {etf_code}的溢价率信息。")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"请求ETF {etf_code}失败: {e}")
        return None

def send_email(subject, body, sender_email, recipient_email, mails_dev_api_key):
    try:
        msg = MIMEText(body, 'html', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        # 使用mails.dev API发送邮件
        response = requests.post(
            "https://api.mails.dev/api/v1/emails/send",
            headers={
                "Content-Type": "application/json",
                "x-api-key": mails_dev_api_key
            },
            json={
                "from": sender_email,
                "to": [recipient_email],
                "subject": subject,
                "text": body,
                "html": body
            }
        )
        response.raise_for_status()
        logging.info(f"邮件发送成功，主题: {subject}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"邮件发送失败: {e}. Response: {e.response.text if e.response else 'N/A'}")
        return False
    except Exception as e:
        logging.error(f"发送邮件时发生错误: {e}")
        return False

def main():
    logging.info("DEBUG: Starting main function and checking environment variables...")

    # Log all environment variables for debugging
    logging.info(f"DEBUG: ETF_CODES env var = '{os.getenv("ETF_CODES")}'")
    logging.info(f"DEBUG: PRICE_THRESHOLD env var = '{os.getenv("PRICE_THRESHOLD")}'")
    logging.info(f"DEBUG: SENDER_EMAIL env var = '{os.getenv("SENDER_EMAIL")}'")
    logging.info(f"DEBUG: RECIPIENT_EMAIL env var = '{os.getenv("RECIPIENT_EMAIL")}'")
    logging.info(f"DEBUG: MAILS_DEV_API_KEY env var = '{os.getenv("MAILS_DEV_API_KEY")}'")

    # Read and process ETF_CODES
    etf_codes_str = os.getenv("ETF_CODES", "159501,513500")
    logging.info(f"DEBUG: ETF_CODES env var (processed) = '{etf_codes_str}'")
    etf_codes = [code.strip() for code in etf_codes_str.split(',') if code.strip()]
    if not etf_codes:
        logging.warning("ETF_CODES is empty or invalid. Using default: '159501,513500'")
        etf_codes = ["159501", "513500"]
    logging.info(f"DEBUG: etf_codes list = {etf_codes}")

    # Read and process PRICE_THRESHOLD
    price_threshold_str = os.getenv("PRICE_THRESHOLD", "3.0")
    logging.info(f"DEBUG: PRICE_THRESHOLD env var (processed) = '{price_threshold_str}'")
    try:
        price_threshold = float(price_threshold_str)
        logging.info(f"DEBUG: price_threshold converted to {price_threshold}")
    except ValueError as e:
        logging.error(f"ERROR: Failed to convert PRICE_THRESHOLD '{price_threshold_str}' to float: {e}")
        price_threshold = 3.0
        logging.info(f"DEBUG: Using default price_threshold = {price_threshold}")

    # Read other email related environment variables
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    mails_dev_api_key = os.getenv("MAILS_DEV_API_KEY")

    if not sender_email:
        logging.error("SENDER_EMAIL environment variable is not set. Exiting.")
        return
    if not recipient_email:
        logging.error("RECIPIENT_EMAIL environment variable is not set. Exiting.")
        return
    if not mails_dev_api_key:
        logging.error("MAILS_DEV_API_KEY environment variable is not set. Exiting.")
        return

    logging.info(f"DEBUG: SENDER_EMAIL = {sender_email}")
    logging.info(f"DEBUG: RECIPIENT_EMAIL = {recipient_email}")
    logging.info(f"DEBUG: MAILS_DEV_API_KEY is set (value not logged for security)")

    all_etf_data = {}
    
    # 模拟在非工作时间（如凌晨）不进行详细溢价率检查和邮件发送
    current_time = time.localtime()
    hour = current_time.tm_hour
    
    # 定义工作时间 (例如 9:00 - 16:00)
    is_trading_hours = 9 <= hour < 16

    for code in etf_codes:
        logging.info(f"正在获取ETF {code}的数据...")
        premium_rate = get_etf_data(code)
        if premium_rate is not None:
            all_etf_data[code] = premium_rate
            logging.info(f"ETF {code} 溢价率: {premium_rate}%")
            if is_trading_hours and premium_rate < price_threshold:
                subject = f"ETF {code} 溢价率提醒: {premium_rate}%"
                body = f"ETF {code} 当前溢价率: {premium_rate}%，已低于设定的 {price_threshold}%。"
                send_email(subject, body, sender_email, recipient_email, mails_dev_api_key)
        time.sleep(2) # 避免请求过快

    # 每天早上9:40发送数据汇总 (如果满足条件，且不是在其他调度运行的通知邮件)
    if current_time.tm_min == 40 and hour == 9:
        summary_body = "<h3>ETF 溢价率每日汇总</h3>"
        if all_etf_data:
            for code, rate in all_etf_data.items():
                summary_body += f"<p>ETF {code}: {rate}%</p>"
        else:
            summary_body += "<p>未能获取任何ETF数据。</p>"
        
        send_email("ETF 溢价率每日汇总", summary_body, sender_email, recipient_email, mails_dev_api_key)
        
if __name__ == "__main__":
    main()
