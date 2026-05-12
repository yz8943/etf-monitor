# ETF Monitor

这是一个用于监控ETF溢价率的系统。它会定期爬取指定ETF的溢价率，当溢价率低于设定的阈值时，通过邮件发送提醒。系统还会每天早上9:40发送当日ETF溢价率的汇总邮件。

## 功能特点

- **ETF数据抓取**: 从`wise-etf.com`抓取ETF的实时溢价率数据。
- **溢价率提醒**: 当ETF溢价率低于设定阈值时，自动发送邮件提醒。
- **每日数据汇总**: 每天早上9:40发送一次当日ETF溢价率的汇总邮件。
- **GitHub Actions集成**: 通过GitHub Actions实现自动化定时运行。

## 监控的ETF

您可以配置要监控的ETF代码。

## 技术栈

- Python 3.9+
- `requests` 用于HTTP请求
- `beautifulsoup4` 和 `lxml` 用于HTML解析
- `python-dotenv` 用于本地环境变量管理
- `mails.dev` API 用于邮件发送

## 部署与配置

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/etf-monitor.git
cd etf-monitor
```

### 2. 设置环境变量

本系统依赖以下环境变量来运行。您可以在GitHub Actions中配置Secrets，或者在本地创建一个`.env`文件进行测试。

- `MAILS_DEV_API_KEY`: mails.dev的API Key，用于发送邮件。
- `SENDER_EMAIL`: 发件人邮箱地址。
- `RECIPIENT_EMAIL`: 收件人邮箱地址。
- `ETF_CODES`: 以逗号分隔的ETF代码列表，例如：`159501,513500`。 (可选，默认监控159501, 513500)
- `PRICE_THRESHOLD`: 溢价率提醒的阈值，例如：`3.0` 表示3%。 (可选，默认为3.0)

#### `.env` 文件示例 (`config.example.env`)

```
MAILS_DEV_API_KEY="your_mails_dev_api_key"
SENDER_EMAIL="your_sender_email@example.com"
RECIPIENT_EMAIL="your_recipient_email@example.com"
ETF_CODES="159501,513500"
PRICE_THRESHOLD="3.0"
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 本地运行 (测试)

```bash
python monitor.py
```

### 5. GitHub Actions 部署

1. 在您的GitHub仓库中，前往 `Settings` -> `Secrets` -> `Actions`。
2. 添加以下Secrets：
   - `MAILS_DEV_API_KEY`
   - `SENDER_EMAIL`
   - `RECIPIENT_EMAIL`
   - `ETF_CODES` (可选)
   - `PRICE_THRESHOLD` (可选)
3. 确保 `.github/workflows/etf-monitor.yml` 文件存在于您的仓库中。
4. GitHub Actions将根据`.github/workflows/etf-monitor.yml`中定义的cron表达式自动运行您的监控脚本。

## 注意事项

- 邮件发送频率受`mails.dev`服务限制，请查阅其文档。
- ETF数据抓取频率不宜过高，以免被目标网站封禁IP。
- 本脚本仅作为示例，实际使用请根据您的需求进行调整和优化。
