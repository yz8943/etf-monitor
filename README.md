# ETF Monitor

这是一个用于监控 ETF 溢价率并发送邮件通知的系统。系统会在工作日每 10 分钟检查一次指定 ETF 的溢价率，并在溢价率低于 3% 时发送邮件提醒。此外，系统还会在每个工作日早上 9:40 发送一份当日 ETF 数据汇总邮件。

## 功能特点

- **实时监控**：每 10 分钟查询一次 ETF 溢价率。
- **邮件通知**：溢价率低于阈值时即时提醒，每日汇总报告。
- **GitHub Actions 部署**：无需外部服务器，利用 GitHub Actions 自动运行。
- **可配置**：通过环境变量轻松配置监控 ETF 列表、邮件发送设置等。

## 监控的 ETF

- 159501 (纳指ETF)
- 513500 (半导体ETF)

## 数据源

数据来源于 [wise-etf.com](https://www.wise-etf.com/etf).

## 安装指南

1. **克隆仓库**：
   ```bash
   git clone https://github.com/yz8943/etf-monitor.git
   cd etf-monitor
   ```

2. **创建虚拟环境 (可选但推荐)**：
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # venv\Scripts\activate  # Windows
   ```

3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

4. **设置环境变量**：
   在 GitHub 仓库的 `Settings` -> `Secrets` -> `Actions` 中添加以下 Secrets：
   - `SENDER_EMAIL`: 发送邮件的邮箱地址 (例如: `kerry@mails.dev`)
   - `MAIL_API_KEY`: mails.dev 生成的 API Key (例如: `mk_1562057e9e7f4e94867ff171c72cda3d`)
   - `RECIPIENT_EMAIL`: 接收通知的邮箱地址 (例如: `yangzhi72@126.com`)

   或者在本地测试时，可以创建一个 `.env` 文件 (请参考 `config.example.env`)，内容如下：
   ```
   SENDER_EMAIL=your_sender_email@example.com
   MAIL_API_KEY=your_mails_dev_api_key
   RECIPIENT_EMAIL=your_recipient_email@example.com
   ```

## 使用说明

本项目主要通过 GitHub Actions 自动运行。您不需要手动执行脚本。配置好 GitHub Actions Secrets 后，它将按照预定的时间表自动工作。

如果您想在本地测试或手动运行，可以使用以下命令：

- **运行常规监控**：
  ```bash
  python monitor.py
  ```

- **生成每日汇总**：
  ```bash
  python monitor.py summary
  ```

## 自定义监控 ETF

您可以通过修改 `monitor.py` 文件中的 `ETFS` 字典来添加或删除监控的 ETF：

```python
ETFS = {
    "159501": "纳指ETF",
    "513500": "半导体ETF",
    # "您的ETF代码": "ETF名称",
}
```

## 日志

脚本运行日志将记录到 `etf_monitor.log` 文件中。

## 注意事项

- 请确保您的 `MAIL_API_KEY` 是有效的，并且 `SENDER_EMAIL` 在 mails.dev 中已验证。
- GitHub Actions 的 `cron` 表达式以 UTC 时间为准。请根据您的需要调整。
