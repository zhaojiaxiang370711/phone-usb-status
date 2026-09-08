# 参与贡献

欢迎提交 bug 报告、兼容性记录、文档改进与 Pull Request。

## 本地开发

```bash
git clone https://github.com/zhaojiaxiang370711/phone-usb-status.git
cd phone-usb-status
python3 -m unittest discover -v
node --check app.js
```

运行页面请按 README 创建本地配置。修改前后运行测试；新设备识别规则应提供虚构 sysfs 数据的测试，不要求贡献者连接真实手机。

## 提交问题

请说明 Linux 发行版、Python 版本、ADB/Fastboot 版本、复现步骤、期望与实际状态。脱敏后再提供日志或截图，不要提交真实序列号、SIM PIN、设备凭据、固件或分区备份。

目前支持范围以 README 为准。添加其他机型时，请明确哪些功能经过实机验证，哪些只是代码或模拟测试通过。

## Pull Request

- 简述问题、改动和验证方式，保持修改聚焦。
- 保留本机回环监听、严格设备匹配与检测失败显示未知的行为。
- 不引入刷写、擦除、重启或任意命令执行接口。
- 不增加遥测、第三方远程资源或敏感信息日志。
- 不把示例设备标识当作真实设备配置。

贡献代码将按本项目的 MIT 许可证分发。
