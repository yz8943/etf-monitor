# ETF Monitor

监控 ETF 溢价率的自动化工具。优先从 spxnasdaq.top 获取实时数据（含代码、名称、规模、最新价、净值、溢价率、当日涨跌），当溢价率低于阈值时通过邮件发送 HTML 表格格式的提醒，每天早上 9:40 发送汇总邮件。

## 功能

- 优先从 spxnasdaq.top 抓取 ETF 数据（失败自动回退到 wise-etf.com）
- 邮件以 HTML 表格展示：代码、名称、规模、最新价、净值、溢价率、当日涨跌
- 溢价率低于阈值时自动发邮件提醒（溢价率低于 3% 显示绿色，高于显示红色）
- 每天早上 9:40 发送当日汇总
- GitHub Actions 定时运行（每 10 分钟检查一次）

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `MAILS_DEV_API_KEY` | 是 | mails.dev 托管服务的 API Key |
| `SENDER_EMAIL` | 是 | 发件人地址（需与 mails.dev 认领的邮箱一致） |
| `RECIPIENT_EMAIL` | 是 | 收件人地址 |
| `ETF_CODES` | 否 | ETF 代码，逗号分隔，默认 `159501,513500` |
| `PRICE_THRESHOLD` | 否 | 溢价率阈值（%），默认 `3.0` |

### 获取 mails.dev API Key

1. 安装 CLI：`npm install -g mails`
2. 认领邮箱：`mails claim myagent`（获得 `myagent@mails.dev`）
3. 查看配置：`mails config`，其中的 `api_key` 即为 `MAILS_DEV_API_KEY`

### `.env` 文件示例

```
MAILS_DEV_API_KEY="your_api_key"
SENDER_EMAIL="myagent@mails.dev"
RECIPIENT_EMAIL="your_email@example.com"
ETF_CODES="159501,513500"
PRICE_THRESHOLD="3.0"
```

## 本地运行

```bash
pip install -r requirements.txt

# 测试邮件发送（确认 mails.dev 配置正确）
python test_email.py

# 运行监控
python monitor.py
```

## GitHub Actions 部署

1. 在仓库 `Settings` -> `Secrets` -> `Actions` 中添加上述环境变量
2. `.github/workflows/etf-monitor.yml` 已配置好，工作日 9:00-16:00 每 10 分钟运行一次

## 项目结构

```
monitor.py           # 主程序（数据获取 + 邮件推送）
test_email.py        # 邮件发送测试
requirements.txt     # Python 依赖（requests, python-dotenv, beautifulsoup4）
premium_history.json # 溢价率历史记录（自动生成）
```

## 数据源

| 优先级 | 来源 | 获取方式 | 字段 |
|---|---|---|---|
| 1 | spxnasdaq.top | HTML 表格解析（BeautifulSoup） | 代码、名称、规模、最新价、净值、溢价率、当日涨跌 |
| 2 | wise-etf.com | `/api/etfs` JSON API | 代码、名称、溢价率（回退源，字段较少） |
