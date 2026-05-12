
import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging
import time
import json
from datetime import datetime

        
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

def load_premium_history():
    """加载历史溢价率记录"""
    try:
        with open('premium_history.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_premium_history(data):
    """保存历史溢价率记录"""
    with open('premium_history.json', 'w') as f:
        json.dump(data, f, indent=2)

def main():
    current_time = datetime.now()
    hour = current_time.hour
    minute = current_time.minute
    today = current_time.strftime("%Y-%m-%d")
    
    history = load_premium_history()
    
    # 检查是否需要重置当天计数（早上9:40）
    last_reset = history.get("last_reset_date")
    if last_reset != today:
        history["daily_emails_sent"] = 0
        history["last_reset_date"] = today
    
    etf_codes = os.getenv("ETF_CODES", "159501,513500").split(",")
    THRESHOLD= os.getenv("PRICE_THRESHOLD", "3.0")
    price_threshold = float(THRESHOLD)
    
    emails_to_send = []
    
    for code in etf_codes:
        code = code.strip()
        premium = get_premium_rate(code)  # 你现有的函数
        
        if premium is None:
            continue
        
        # 9:40 固定发送汇总邮件
        if hour == 9 and minute == 40:
            emails_to_send.append({
                "type": "summary",
                "code": code,
                "premium": premium,
                "message": f"{code} 当前溢价率: {premium:.2f}%"
            })
        # 其他时间：只有当溢价 < 3% 且 < 上次溢价时才发
        elif premium < price_threshold and history["daily_emails_sent"] < 2:
            last_premium = history.get(code, {}).get("last_premium")
            if last_premium is None or premium < last_premium:
                emails_to_send.append({
                    "type": "alert",
                    "code": code,
                    "premium": premium,
                    "message": f"{code} 溢价下降到 {premium:.2f}%，低于 {price_threshold}% 阈值，强烈推荐！"
                })
    
    # 发送邮件
    if emails_to_send:
        send_email(emails_to_send)
        history["daily_emails_sent"] += 1
    
    # 更新历史记录
    for code in etf_codes:
        code = code.strip()
        premium = get_premium_rate(code)
        if premium is not None:
            if code not in history:
                history[code] = {}
            history[code]["last_premium"] = premium
            history[code]["last_update"] = today
    
    save_premium_history(history)
        
if __name__ == "__main__":
    main()
