# Phone USB Status

A local-only USB status dashboard extracted from Xiaomi 11 Pro (mars) Linux bring-up work. Python standard library backend, plain HTML/CSS/JavaScript frontend, MIT licensed.

## Quick start

Requires Linux, Python 3.10+, `adb` and `fastboot`, and appropriate USB permissions.

```bash
git clone https://github.com/zhaojiaxiang370711/phone-usb-status.git
cd phone-usb-status
cp config.example.json config.local.json
chmod 600 config.local.json
# Set your device serial and EDL chip ID in config.local.json.
python3 server.py
```

Open http://127.0.0.1:8787/ . Use `--port` or `--config` to override defaults. `serial` is the device's ADB/Fastboot serial; `edl_chip_id` is the hexadecimal identifier after `_SN:` in its USB product descriptor. The example values are placeholders. Local configuration is ignored by Git.

The dashboard polls every two seconds, shows recent transitions, and distinguishes unavailable detection from disconnection. EDL is read from sysfs without opening USB endpoints or calling ADB/Fastboot. Other modes use bounded `devices` queries; ADB may start its local daemon. There are no flash, erase, reboot or arbitrary command endpoints.

The UI and RAM Linux matching currently target mars. USB enumeration does not establish a working Linux session, loaded EDL programmer, or verified recovery path. Windows and macOS are not supported.

## One-time PIN inbox

An optional-use form holds a SIM PIN in process memory for up to five minutes and clears its temporary buffer after one read. It does not verify the PIN against the SIM. No PIN is written to application files or access logs. Full erasure of all Python/browser memory copies cannot be guaranteed.

This service is for a trusted local machine only. Other local processes can access its APIs. Do not expose it through a proxy or tunnel. See [security notes](SECURITY.md).

## Tests

```bash
python3 -m unittest discover -v
node --check app.js
```

Tests use synthetic identities and do not need a phone. See the [Chinese README](README.md) for API details, [contribution guide](CONTRIBUTING.md) and [MIT license](LICENSE).
