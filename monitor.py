import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE_URL = "https://palmmicro.com/woody/res/qdiicn.php"
USER_AGENT = "Mozilla/5.0"
CODE_PATTERN = re.compile(r"^(?:[A-Z]{2})?\d{6}$")
MONITORED_CODES = ("SZ159501", "SH513500")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_env_file(path):
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


for env_file in ("config.env", ".env"):
    load_env_file(env_file)


def filter_monitored_etfs(etf_rows):
    monitored = [row for row in etf_rows if row.get("code") in MONITORED_CODES]
    monitored.sort(key=lambda item: MONITORED_CODES.index(item.get("code")))
    return monitored


def prune_history(history):
    preserved = {
        key: value
        for key, value in history.items()
        if key in {"daily_emails_sent", "daily_summary_sent", "last_reset_date"} or key in MONITORED_CODES
    }
    return preserved


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table = []
        self._current_row = []
        self._current_cell = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._in_cell:
            text = " ".join(part.strip() for part in self._current_cell if part.strip())
            self._current_row.append(re.sub(r"\s+", " ", text).strip())
            self._in_cell = False
            self._current_cell = []
        elif tag == "tr" and self._in_row:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._in_row = False
            self._current_row = []
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False
            self._current_table = []

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell.append(data)


def _clean_text(value):
    return " ".join(value.split())


def _safe_get(values, index):
    if index is None or index < 0 or index >= len(values):
        return ""
    return values[index]


def _find_index(headers, *keywords):
    for index, header in enumerate(headers):
        if all(keyword in header for keyword in keywords):
            return index
    return None


def _looks_like_code(value):
    return bool(CODE_PATTERN.match(value.strip()))


def _parse_percent(value):
    try:
        return float(value.replace("%", "").replace("−", "-").replace("—", "-").strip())
    except ValueError:
        return 0.0


def _fetch_url(url, method="GET", headers=None, body=None):
    request = Request(url, data=body, method=method, headers=headers or {})
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_page_tables(html):
    parser = TableParser()
    parser.feed(html)

    base_rows = {}
    premium_rows = {}

    for table in parser.tables:
        cleaned_rows = [[_clean_text(cell) for cell in row] for row in table if any(cell.strip() for cell in row)]
        if not cleaned_rows:
            continue

        header_row = cleaned_rows[0]
        header_text = " ".join(header_row)

        if "代码" in header_text and "名称" in header_text and ("价格" in header_text or "现价" in header_text):
            code_index = _find_index(header_row, "代码")
            name_index = _find_index(header_row, "名称")
            price_index = _find_index(header_row, "价格")
            if price_index is None:
                price_index = _find_index(header_row, "现价")
            change_index = _find_index(header_row, "涨幅")
            if change_index is None:
                change_index = _find_index(header_row, "涨跌")
            date_index = _find_index(header_row, "日期")
            time_index = _find_index(header_row, "时间")

            for row in cleaned_rows[1:]:
                code = _safe_get(row, code_index)
                if not _looks_like_code(code):
                    continue

                base_rows[code] = {
                    "code": code,
                    "name": _safe_get(row, name_index),
                    "latest_price": _safe_get(row, price_index),
                    "daily_change": _safe_get(row, change_index),
                    "date": _safe_get(row, date_index),
                    "time": _safe_get(row, time_index),
                }

        if "EST" in header_text and "溢价" in header_text:
            code_index = _find_index(header_row, "代码")
            official_est_index = _find_index(header_row, "官方", "EST")
            if official_est_index is None:
                official_est_index = _find_index(header_row, "EST")
            est_date_index = _find_index(header_row, "EST日期")
            if est_date_index is None:
                est_date_index = _find_index(header_row, "日期")
            reference_est_index = _find_index(header_row, "参考", "EST")
            realtime_est_index = _find_index(header_row, "实时", "EST")

            for row in cleaned_rows[1:]:
                code = _safe_get(row, code_index)
                if not _looks_like_code(code):
                    continue

                percent_values = [cell for cell in row if "%" in cell]
                premium_value = percent_values[-1] if percent_values else ""
                premium_rows[code] = {
                    "code": code,
                    "official_est": _safe_get(row, official_est_index),
                    "est_date": _safe_get(row, est_date_index),
                    "reference_est": _safe_get(row, reference_est_index),
                    "realtime_est": _safe_get(row, realtime_est_index),
                    "official_premium": percent_values[0] if len(percent_values) > 0 else "",
                    "reference_premium": percent_values[1] if len(percent_values) > 1 else "",
                    "premium": premium_value,
                    "premium_value": _parse_percent(premium_value) if premium_value else 0.0,
                }

    merged_rows = []
    for code, row in premium_rows.items():
        merged = {**row, **base_rows.get(code, {})}
        if not merged.get("name"):
            merged["name"] = code
        if not merged.get("date"):
            merged["date"] = merged.get("est_date", "")
        merged_rows.append(merged)

    for code, row in base_rows.items():
        if code in premium_rows:
            continue
        merged_rows.append(row)

    merged_rows.sort(key=lambda item: item.get("code", ""))
    return merged_rows


def get_etf_data():
    try:
        html = _fetch_url(SOURCE_URL, headers={"User-Agent": USER_AGENT})
        etf_rows = _parse_page_tables(html)
        logging.info("Fetched %d ETF rows from qdiicn.php", len(etf_rows))
        return etf_rows
    except (HTTPError, URLError, TimeoutError) as exc:
        logging.warning("Failed to fetch qdiicn.php: %s", exc)
        return []
    except Exception as exc:
        logging.warning("Unexpected fetch error: %s", exc)
        return []


def send_email(subject, body, sender_email, recipient_email, mails_dev_api_key):
    try:
        payload = json.dumps(
            {
                "from": sender_email,
                "to": [recipient_email],
                "subject": subject,
                "text": body,
                "html": body,
            }
        ).encode("utf-8")

        html = _fetch_url(
            "https://api.mails.dev/v1/send",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {mails_dev_api_key}",
                "User-Agent": USER_AGENT,
            },
            body=payload,
        )
        logging.info("Email sent successfully: %s", subject)
        logging.debug("Mail API response: %s", html)
        return True
    except (HTTPError, URLError, TimeoutError) as exc:
        logging.error("Email send failed: %s", exc)
        return False
    except Exception as exc:
        logging.error("Unexpected email error: %s", exc)
        return False


def load_premium_history():
    try:
        with open("premium_history.json", "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception:
        return {}


def save_premium_history(data):
    with open("premium_history.json", "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2, ensure_ascii=False)


def build_email_html(etf_list, threshold, is_alert=False):
    title = "QDII 溢价提醒" if is_alert else "QDII 每日汇总"
    intro = "以下条目低于阈值，请重点关注。" if is_alert else "以下为 qdiicn.php 表格数据汇总。"
    rows = ""

    for item in etf_list:
        premium_value = item.get("premium_value", 0.0)
        color = "green" if premium_value < threshold else "red"
        rows += f"""<tr>
            <td>{escape(item.get('code', ''))}</td>
            <td>{escape(item.get('name', ''))}</td>
            <td>{escape(item.get('latest_price', ''))}</td>
            <td>{escape(item.get('daily_change', ''))}</td>
            <td>{escape(item.get('official_est', ''))}</td>
            <td>{escape(item.get('realtime_est', '') or item.get('reference_est', ''))}</td>
            <td style="color:{color};font-weight:bold">{escape(item.get('premium', ''))}</td>
            <td>{escape(item.get('date', ''))}</td>
            <td>{escape(item.get('time', ''))}</td>
        </tr>"""

    return f"""<html>
<body style="font-family:Arial,sans-serif;">
    <h3>{escape(title)}</h3>
    <p>{escape(intro)}</p>
    <p>数据源: <a href="{SOURCE_URL}">{SOURCE_URL}</a></p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <tr style="background:#f0f0f0;">
            <th>代码</th><th>名称</th><th>价格</th><th>涨幅</th><th>官方 EST</th><th>实时 EST</th><th>溢价</th><th>日期</th><th>时间</th>
        </tr>
        {rows}
    </table>
</body>
</html>"""


def main():
    current_time = datetime.now(timezone.utc) + timedelta(hours=8)
    hour = current_time.hour
    minute = current_time.minute
    today = current_time.strftime("%Y-%m-%d")

    history = load_premium_history()
    history = prune_history(history)
    last_reset = history.get("last_reset_date")
    if last_reset != today:
        history["daily_emails_sent"] = 0
        history["daily_summary_sent"] = False
        history["last_reset_date"] = today

    threshold = float(os.getenv("PRICE_THRESHOLD", "3.0"))
    etf_data = get_etf_data()
    etf_data = filter_monitored_etfs(etf_data)

    if not etf_data:
        logging.warning("No monitored ETF data fetched, nothing to send.")
        save_premium_history(history)
        return

    alert_etfs = []
    summary_etfs = []

    if not history.get("daily_summary_sent") and (hour > 9 or (hour == 9 and minute >= 30)):
        summary_etfs = list(etf_data)

    if not summary_etfs:
        for etf in etf_data:
            premium_value = etf.get("premium_value", 0.0)
            if premium_value < threshold and history.get("daily_emails_sent", 0) < 2:
                last_premium = history.get(etf["code"], {}).get("last_premium")
                if last_premium is None or premium_value < last_premium:
                    alert_etfs.append(etf)

    if alert_etfs or summary_etfs:
        sender_email = os.getenv("SENDER_EMAIL")
        recipient_email = os.getenv("RECIPIENT_EMAIL")
        api_key = os.getenv("MAILS_DEV_API_KEY")

        missing_values = [
            name
            for name, value in (
                ("MAILS_DEV_API_KEY", api_key),
                ("SENDER_EMAIL", sender_email),
                ("RECIPIENT_EMAIL", recipient_email),
            )
            if not value
        ]
        if missing_values:
            logging.error("Missing required email settings: %s", ", ".join(missing_values))
            save_premium_history(history)
            return

        is_alert = bool(alert_etfs)
        etf_list = alert_etfs if is_alert else summary_etfs
        body = build_email_html(etf_list, threshold, is_alert)
        subject = "QDII 溢价提醒" if is_alert else "QDII 每日汇总"
        if send_email(subject, body, sender_email, recipient_email, api_key):
            history["daily_emails_sent"] = history.get("daily_emails_sent", 0) + 1
            if summary_etfs:
                history["daily_summary_sent"] = True

    for etf in etf_data:
        code = etf["code"]
        if code not in history:
            history[code] = {}
        history[code]["last_premium"] = etf.get("premium_value", 0.0)
        history[code]["last_update"] = today

    save_premium_history(history)


if __name__ == "__main__":
    main()
