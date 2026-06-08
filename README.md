# ETF Monitor

这个项目只使用 `https://palmmicro.com/woody/res/qdiicn.php` 作为数据源，当前只监控 `SZ159501` 和 `SH513500` 两个代码，抓取页面表格后生成邮件并发送提醒。

## 功能

- 直接抓取 `qdiicn.php` 页面
- 只保留 `SZ159501` 和 `SH513500` 两个监控项
- 按页面表格生成 HTML 邮件
- 支持溢价阈值提醒
- 支持每日汇总邮件
- 支持 GitHub Actions 定时执行

## 配置

当前脚本会优先读取 `config.env`，也兼容 `.env`。

| 变量 | 必填 | 说明 |
|---|---|---|
| `MAILS_DEV_API_KEY` | 是 | `mails.dev` API Key |
| `SENDER_EMAIL` | 是 | 发件人地址 |
| `RECIPIENT_EMAIL` | 是 | 收件人地址 |
| `PRICE_THRESHOLD` | 否 | 溢价阈值，默认 `3.0` |

示例：

```env
MAILS_DEV_API_KEY="your_mails_dev_api_key"
SENDER_EMAIL="your_sender_email@example.com"
RECIPIENT_EMAIL="your_recipient_email@example.com"
PRICE_THRESHOLD="3.0"
```

## 运行

直接执行：

```bash
python monitor.py
```

如果要先验证邮件发送配置，可以运行：

```bash
python test_email.py
```

## 说明

- 如果你本地已有 `config.env`，现在脚本会自动读取
- 如果邮件发送返回 `401 Unauthorized`，通常是 `MAILS_DEV_API_KEY` 无效、过期，或者发件配置不匹配
- `premium_history.json` 会记录当天是否已发送汇总和这两个代码最近一次的溢价值

### `premium_history.json` 字段说明

- `daily_emails_sent`：当天已发送的邮件数量
- `daily_summary_sent`：当天是否已经发过汇总邮件
- `last_reset_date`：状态重置日期，按日期切换后会重新计数
- `SH513500` / `SZ159501`：两个监控代码最近一次的溢价值和更新时间

### 本次汇总后的状态

- 当前日期的状态已重置为 `2026-06-08`
- 已发送 `1` 封邮件，且当天汇总邮件已经发送完成
- 本次共记录 `33` 个 ETF/QDII 条目
- 其中 `13` 个条目的最新溢价低于 `3.0%`，会被视为提醒候选
- 其余条目高于或等于阈值，保留为汇总展示数据

## 文件

- `monitor.py`：抓取数据、生成邮件、发送通知
- `test_email.py`：邮件连通性测试
- `config.example.env`：环境变量示例
- `premium_history.json`：历史记录
