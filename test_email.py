"""邮件发送测试脚本，用于验证 mails.dev 配置。"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_env_file(path):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as file_handle:
        for raw_line in file_handle:
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


def send_test_email(api_key, sender, recipient):
    payload = json.dumps(
        {
            "from": sender,
            "to": [recipient],
            "subject": "QDII Monitor 测试邮件",
            "text": "这是一封测试邮件，用于验证 mails.dev 配置是否可用。",
            "html": "<h3>QDII Monitor 测试邮件</h3><p>如果你收到了这封邮件，说明 mails.dev 配置正常。</p>",
        }
    ).encode("utf-8")

    request = Request(
        "https://api.mails.dev/v1/send",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


api_key = os.getenv("MAILS_DEV_API_KEY")
sender = os.getenv("SENDER_EMAIL")
recipient = os.getenv("RECIPIENT_EMAIL")

print(f"API_KEY: {api_key[:8]}..." if api_key else "API_KEY: 未设置")
print(f"SENDER: {sender or '未设置'}")
print(f"RECIPIENT: {recipient or '未设置'}")
print()

if not api_key or not sender or not recipient:
    raise SystemExit("请先在环境变量或 config.env 文件中配置 MAILS_DEV_API_KEY、SENDER_EMAIL 和 RECIPIENT_EMAIL")

print("=== 测试 POST /v1/send ===")
try:
    status, response_text = send_test_email(api_key, sender, recipient)
    print(f"Status: {status}")
    print(f"Response: {response_text}")
except HTTPError as exc:
    print(f"Status: {exc.code}")
    print(f"Response: {exc.read().decode('utf-8', errors='replace')}")
except URLError as exc:
    print(f"Error: {exc}")
except Exception as exc:
    print(f"Error: {exc}")
