
import requests
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime

        
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

def get_etf_data(etf_code):
    url = "https://www.wise-etf.com/api/etfs"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        for etf in response.json().get("data", []):
            if etf["code"] == etf_code:
                premium = etf["premium"]
                logging.info(f"ETF {etf_code} ({etf['name']}) 溢价率: {premium}%")
                return float(premium)

        logging.error(f"未找到 ETF {etf_code}")
        return None

    except Exception as e:
        logging.error(f"获取ETF {etf_code}失败: {e}")
        return None
            

def send_email(subject, body, sender_email, recipient_email, mails_dev_api_key):
    try:
        response = requests.post(
            "https://api.mails.dev/api/send",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {mails_dev_api_key}"
            },
            json={
                "from": sender_email,
                "to": recipient_email,
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
    threshold = os.getenv("PRICE_THRESHOLD")
    if not threshold:
        threshold = "3.0"
    price_threshold = float(threshold)
    
    emails_to_send = []
    
    for code in etf_codes:
        code = code.strip()
        premium = get_etf_data(code)  # 你现有的函数
        
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
        sender_email = os.getenv("SENDER_EMAIL")
        recipient_email = os.getenv("RECIPIENT_EMAIL")
        api_key = os.getenv("MAILS_DEV_API_KEY")

        body = "<br>".join(e["message"] for e in emails_to_send)
        subject = "ETF 溢价率提醒" if any(e["type"] == "alert" for e in emails_to_send) else "ETF 每日汇总"
        send_email(subject, body, sender_email, recipient_email, api_key)
        history["daily_emails_sent"] += 1
    
    # 更新历史记录
    for code in etf_codes:
        code = code.strip()
        premium = get_etf_data(code)
        if premium is not None:
            if code not in history:
                history[code] = {}
            history[code]["last_premium"] = premium
            history[code]["last_update"] = today
    
    save_premium_history(history)
        
if __name__ == "__main__":
    main()
