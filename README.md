# Phone USB Status

为小米 11 Pro（mars）Linux 适配开发提取的本机 USB 状态面板。Python 标准库后端与原生 HTML/CSS/JavaScript 前端，无第三方 Python 依赖。

## 功能

- 每 2 秒检测 9008/EDL、ADB（正常、未授权、离线）、Fastboot 和 RAM Linux 诊断 USB。
- 显示 USB 标识、设备身份、访问权限与最近状态变化。
- 检测失败或网页数据过期时显示未知/中断，不把旧状态当成实时结果。
- 保留一次性 SIM PIN 内存暂存功能，默认 5 分钟过期，读取后清除暂存缓冲区。

## 启动

要求 Linux、Python 3.10+，ADB/Fastboot 命令可用（Ubuntu 对应 `adb`、`fastboot` 包），当前用户具备必要的 USB 访问权限。

```bash
cp config.example.json config.local.json
chmod 600 config.local.json
# 编辑 config.local.json，填写自己的 ADB/Fastboot 序列号和 EDL 芯片标识
python3 server.py
```

浏览器打开 http://127.0.0.1:8787/ 。可通过 `--port 8788` 更换端口，或 `--config /path/to/config.local.json` 指定配置。

`serial` 使用 ADB/Fastboot 的实际目标序列号；`edl_chip_id` 使用设备 USB product 描述中 `_SN:` 后的完整十六进制标识。示例值不是设备配置。配置缺失或格式不正确时启动失败。真实配置已被 Git 忽略。

当前界面、RAM Linux 标识规则仍针对 mars，不代表已适配所有 Android 手机。9008 身份仅核对 USB 描述符，不是密码学设备认证。

## 检测边界

EDL 通过 Linux sysfs 枚举，不打开 USB 端点、不加载引导，也不调用 ADB/Fastboot。其余模式调用有超时限制的 `adb devices` / `fastboot devices`；ADB 命令可能自动启动本机 ADB server。没有刷写、擦除、重启或自定义命令接口。

9008 已连接不代表引导已加载或恢复流程验证通过。RAM Linux USB 已枚举不证明内核及用户空间仍然正常运行。此工具应运行在连接手机的电脑上，不应部署到公网服务器。

## 本机接口

- `GET /api/status`：当前设备状态与内存中的事件记录。
- `GET /api/pin/status`：是否有待使用 PIN 与剩余秒数，不返回 PIN。
- `POST /api/pin`：JSON 格式的 `pin` 字段，仅接受 4–8 位 ASCII 数字。
- `POST /api/pin/consume`：带 `X-Mars-Pin-Consumer: codex-local-v1` 请求头，读取一次后清除暂存值。

固定消费者请求头不是认证密钥；同一台电脑的其他进程可能访问接口。PIN 不写文件或访问日志，服务重启后丢失；缓冲区清除不等于 Python/浏览器所有内存副本都能保证擦除。仅在可信本机环境使用。

## 检查

```bash
python3 -m unittest discover -v
node --check app.js
```

独立仓库只包含页面、服务、测试和配置示例，不包含手机固件、分区备份、真实设备配置或历史操作日志。
