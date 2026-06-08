# ETF Monitor

这是一个基于 `https://palmmicro.com/woody/res/qdiicn.php` 的 QDII/ETF 监控脚本。

项目现在只保留这一条数据源，不再回退到旧站点。

## 功能

- 直接抓取 `qdiicn.php` 页面表格
- 按表格内容生成 HTML 邮件
- 当溢价低于阈值时发送提醒邮件
- 支持每日汇总邮件
- 可通过 GitHub Actions 定时运行

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `MAILS_DEV_API_KEY` | 是 | `mails.dev` API Key |
| `SENDER_EMAIL` | 是 | 发件人地址 |
| `RECIPIENT_EMAIL` | 是 | 收件人地址 |
| `PRICE_THRESHOLD` | 否 | 溢价阈值，默认 `3.0` |

## 配置示例

把 `config.example.env` 复制成 `.env`，然后填入你的配置：

```env
MAILS_DEV_API_KEY="your_mails_dev_api_key"
SENDER_EMAIL="your_sender_email@example.com"
RECIPIENT_EMAIL="your_recipient_email@example.com"
PRICE_THRESHOLD="3.0"
```

## 执行

这个项目已经改成标准库版，不需要额外安装第三方依赖。

```bash
python monitor.py
```

## GitHub Actions

仓库中的 `.github/workflows/etf-monitor.yml` 会按计划运行 `monitor.py`，并在成功后更新 `premium_history.json`。

## 文件说明

- `monitor.py`：抓取页面、生成邮件、发送通知
- `premium_history.json`：历史溢价记录
- `config.example.env`：环境变量示例
