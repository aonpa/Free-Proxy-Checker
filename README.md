# Free Proxy Checker

A small desktop app for Windows and Linux that loads a proxy list from a text file, checks each entry in parallel, and lets you export working and failed proxies.

Built with Python, [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), and `requests`.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- Dark UI with live stats (loaded / valid / invalid / progress)
- Configurable thread count and request timeout
- Color-coded activity log
- Export valid or invalid proxies to `.txt`

## Download (no Python required)

Pre-built binaries are attached to [GitHub Releases](https://github.com/aonpa/Free-Proxy-Checker/releases) when the build workflow completes:

| Platform | File |
|----------|------|
| Windows | `FreeProxyChecker-Windows.exe` |
| Linux | `FreeProxyChecker-Linux` |

1. Open **Releases** on this repository.
2. Download the file for your OS.
3. **Windows:** run the `.exe`.  
4. **Linux:** `chmod +x FreeProxyChecker-Linux` then `./FreeProxyChecker-Linux`.

> First run on Windows may show SmartScreen — choose *More info* → *Run anyway* if you built or downloaded from this repo’s Actions/Releases.

## Run from source

### Requirements

- Python **3.11** or newer  
- Internet access (proxies are tested against `http://httpbin.org/ip`)

### Install

```bash
git clone https://github.com/aonpa/Free-Proxy-Checker.git
cd Free-Proxy-Checker
python -m pip install -r requirements.txt
```

### Start the app

```bash
python main.py
```

## How to use

1. **Load proxy list** — choose a `.txt` file. One proxy per line, for example:
   ```
   203.0.113.10:8080
   user:pass@203.0.113.11:3128
   http://203.0.113.12:80
   ```
2. Set **Threads** (default `50`) and **Timeout** in seconds (default `5`).
3. Click **Start scan**. Use **Stop scan** to cancel.
4. When finished, use **Export valid** or **Export invalid** to save results.

## Proxy list format

- `host:port`
- `user:pass@host:port`
- Optional scheme: `http://…` or `https://…` (otherwise HTTP is assumed)

Lines without `:` are skipped.

## Build locally

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name FreeProxyChecker-Windows main.py
```

On Linux, omit `--windowed` if you prefer a console build.

## Contributing

Issues and small fixes are welcome. Please keep changes focused; `main.py` is the whole application.

## License

MIT — see [LICENSE](LICENSE).
