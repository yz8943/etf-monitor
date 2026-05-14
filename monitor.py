
import requests
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()


def _get_etf_data_from_spxnasdaq(etf_code):
    try:
        response = requests.get(
            "https://www.spxnasdaq.top/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 7:
                    continue
                if cells[0].get_text(strip=True) == etf_code:
                    name = cells[1].get_text(strip=True)
                    scale = cells[2].get_text(strip=True)
                    latest_price = cells[3].get_text(strip=True)
                    nav = cells[4].get_text(strip=True)
                    premium_str = cells[5].get_text(strip=True).replace('%', '')
                    daily_change = cells[6].get_text(strip=True)
                    try:
                        premium = float(premium_str)
                    except ValueError:
                        premium = 0.0

                    logging.info(f"[spxnasdaq] ETF {etf_code} ({name}) 溢价率: {premium}%")
                    return {
                        "code": etf_code,
                        "name": name,
                        "scale": scale,
                        "latest_price": latest_price,
                        "nav": nav,
                        "premium": premium,
                        "daily_change": daily_change
                    }

        logging.warning(f"[spxnasdaq] 未找到 ETF {etf_code}")
        return None
    except Exception as e:
        logging.warning(f"[spxnasdaq] 获取 ETF {etf_code} 失败: {e}")
        return None


def _get_etf_data_from_wiseetf(etf_code):
    url = "https://www.wise-etf.com/api/etfs"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        for etf in response.json().get("data", []):
            if etf["code"] == etf_code:
                premium = float(etf["premium"])
                name = etf.get("name", "")
                logging.info(f"[wise-etf] ETF {etf_code} ({name}) 溢价率: {premium}%")
                return {
                    "code": etf_code,
                    "name": name,
                    "scale": "",
                    "latest_price": "",
                    "nav": "",
                    "premium": premium,
                    "daily_change": ""
                }
        logging.error(f"[wise-etf] 未找到 ETF {etf_code}")
        return None
    except Exception as e:
        logging.error(f"[wise-etf] 获取 ETF {etf_code} 失败: {e}")
        return None


def get_etf_data(etf_code):
    data = _get_etf_data_from_spxnasdaq(etf_code)
    if data:
        return data
    logging.info(f"回退到 wise-etf.com 获取 ETF {etf_code}")
    return _get_etf_data_from_wiseetf(etf_code)


def send_email(subject, body, sender_email, recipient_email, mails_dev_api_key):
    try:
        response = requests.post(
            "https://api.mails.dev/v1/send",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {mails_dev_api_key}"
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
    try:
        with open('premium_history.json', 'r') as f:
            return json.load(f)
    except:
        return {}


def save_premium_history(data):
    with open('premium_history.json', 'w') as f:
        json.dump(data, f, indent=2)


def build_email_html(etf_list, is_alert=False):
    rows = ""
    for e in etf_list:
        color = "green" if e["premium"] < 3 else "red"
        rows += f"""<tr>
            <td>{e['code']}</td>
            <td>{e['name']}</td>
            <td>{e['scale']}</td>
            <td>{e['latest_price']}</td>
            <td>{e['nav']}</td>
            <td style="color:{color};font-weight:bold">{e['premium']:.2f}%</td>
            <td>{e['daily_change']}</td>
        </tr>"""

    header = "<p>以下 ETF 溢价率低于阈值，推荐关注：</p>" if is_alert else ""
    return header + f"""<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:Arial,sans-serif;">
    <tr style="background:#f0f0f0;">
        <th>代码</th><th>名称</th><th>规模</th><th>最新价</th><th>净值</th><th>溢价率</th><th>当日涨跌</th>
    </tr>
    {rows}
</table>"""


def main():
    current_time = datetime.utcnow() + timedelta(hours=8)
    hour = current_time.hour
    minute = current_time.minute
    today = current_time.strftime("%Y-%m-%d")

    history = load_premium_history()

    last_reset = history.get("last_reset_date")
    if last_reset != today:
        history["daily_emails_sent"] = 0
        history["last_reset_date"] = today

    etf_codes = os.getenv("ETF_CODES", "159501,513500").split(",")
    threshold = os.getenv("PRICE_THRESHOLD")
    if not threshold:
        threshold = "3.0"
    price_threshold = float(threshold)

    alert_etfs = []
    summary_etfs = []
    all_etf_data = {}

    for code in etf_codes:
        code = code.strip()
        etf = get_etf_data(code)
        if etf is None:
            continue

        all_etf_data[code] = etf
        premium = etf["premium"]

        if hour == 9 and 35 <= minute <= 55:
            summary_etfs.append(etf)
        elif premium < price_threshold and history["daily_emails_sent"] < 2:
            last_premium = history.get(code, {}).get("last_premium")
            if last_premium is None or premium < last_premium:
                alert_etfs.append(etf)

    if alert_etfs or summary_etfs:
        sender_email = os.getenv("SENDER_EMAIL")
        recipient_email = os.getenv("RECIPIENT_EMAIL")
        api_key = os.getenv("MAILS_DEV_API_KEY")

        is_alert = bool(alert_etfs)
        etf_list = alert_etfs if is_alert else summary_etfs
        body = build_email_html(etf_list, is_alert)
        subject = "ETF 溢价率提醒" if is_alert else "ETF 每日汇总"
        send_email(subject, body, sender_email, recipient_email, api_key)
        history["daily_emails_sent"] += 1

    for code, etf in all_etf_data.items():
        if code not in history:
            history[code] = {}
        history[code]["last_premium"] = etf["premium"]
        history[code]["last_update"] = today

    save_premium_history(history)


if __name__ == "__main__":
    main()
