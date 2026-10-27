# Free Proxy Checker

Python + CustomTkinter GUI in `main.py`.

- Entry: `python main.py`
- Dependencies: `requirements.txt`
- CI builds PyInstaller artifacts in `.github/workflows/build.yml`

When suggesting changes, prefer minimal diffs in `main.py`. The app uses a background scan thread, a `queue` for log/progress messages, and `after()` on the main window to refresh the UI.
