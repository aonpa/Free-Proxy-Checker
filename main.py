import queue
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox

import customtkinter as ctk
import requests
from PIL import Image, ImageDraw, ImageTk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Palette
BG = "#030008"
SURFACE = "#0e051a"
SURFACE_ALT = "#120820"
BORDER = "#1e1b4b"
ACCENT = "#8b5cf6"
ACCENT_HOVER = "#7c3aed"
DANGER = "#ef4444"
DANGER_HOVER = "#dc2626"
MUTED = "#94a3b8"
SUCCESS = "#22c55e"
FAIL = "#f87171"
FONT_UI = ("Segoe UI", 12)
FONT_UI_BOLD = ("Segoe UI", 13, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_MONO = ("Consolas", 11)
LOG_MAX_LINES = 600
PROGRESS_SUPERSAMPLE = 4


def _hex_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return r, g, b, alpha


class SmoothProgressBar(ctk.CTkFrame):

    def __init__(
        self,
        master,
        bar_height: int = 10,
        track_color: str = BG,
        fill_color: str = ACCENT,
        canvas_bg: str = SURFACE,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._bar_height = bar_height
        self._track_color = track_color
        self._fill_color = fill_color
        self._canvas_bg = canvas_bg
        self._ratio = 0.0
        self._photo: ImageTk.PhotoImage | None = None
        self._canvas = tk.Canvas(
            self,
            height=bar_height,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=canvas_bg,
        )
        self._canvas.pack(fill="x", expand=True)
        self._canvas.bind("<Configure>", self._on_resize)

    def set(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self._render()

    def _on_resize(self, _event=None) -> None:
        self._render()

    def _render(self) -> None:
        width = self._canvas.winfo_width()
        if width < 4:
            self.after(16, self._render)
            return

        height = self._bar_height
        scale = PROGRESS_SUPERSAMPLE
        sw, sh = width * scale, height * scale
        img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        radius = sh // 2
        track = _hex_rgba(self._track_color)
        fill = _hex_rgba(self._fill_color)

        draw.rounded_rectangle((0, 0, sw - 1, sh - 1), radius=radius, fill=track)
        if self._ratio > 0:
            fw = max(int(sw * self._ratio), sh)
            draw.rounded_rectangle((0, 0, fw - 1, sh - 1), radius=radius, fill=fill)

        img = img.resize((width, height), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self._canvas.configure(height=height)


class ProxyCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Free Proxy Checker")
        self.geometry("920x720")
        self.minsize(800, 600)
        self.configure(fg_color=BG)

        self.proxies: list[str] = []
        self.valid_proxies: list[str] = []
        self.invalid_proxies: list[str] = []
        self.is_running = False
        self._checked = 0
        self._ui_queue: queue.Queue = queue.Queue()
        self._list_lock = threading.Lock()
        self._progress_target = 0.0
        self._progress_shown = 0.0

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main()
        self.after(50, self._poll_ui)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, fg_color=SURFACE, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=24, pady=(28, 20))
        ctk.CTkLabel(
            brand,
            text="Free",
            font=FONT_TITLE,
            text_color=ACCENT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text="Proxy Checker",
            font=("Segoe UI", 11),
            text_color=MUTED,
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=20, pady=(0, 12))

        self.threads_entry = self._create_input("Threads", "50")
        self.timeout_entry = self._create_input("Timeout (seconds)", "5")

        self._btn_style = {
            "corner_radius": 14,
            "height": 40,
            "font": FONT_UI_BOLD,
            "fg_color": ACCENT,
            "hover_color": ACCENT_HOVER,
        }
        ctk.CTkButton(
            self.sidebar, text="Load proxy list", command=self.load_proxies, **self._btn_style
        ).pack(pady=(8, 6), padx=20, fill="x")

        self.btn_scan = ctk.CTkButton(
            self.sidebar,
            text="Start scan",
            command=self.toggle_scan,
            **self._btn_style,
        )
        self.btn_scan.pack(pady=6, padx=20, fill="x")

        export_style = {
            **self._btn_style,
            "fg_color": SURFACE_ALT,
            "hover_color": BORDER,
            "border_width": 1,
            "border_color": BORDER,
            "font": FONT_UI,
        }
        ctk.CTkButton(
            self.sidebar,
            text="Export valid",
            command=lambda: self.export(self.valid_proxies, "Valid"),
            **export_style,
        ).pack(pady=(16, 4), padx=20, fill="x")
        ctk.CTkButton(
            self.sidebar,
            text="Export invalid",
            command=lambda: self.export(self.invalid_proxies, "Invalid"),
            **export_style,
        ).pack(pady=4, padx=20, fill="x")

        ctk.CTkLabel(
            self.sidebar,
            text="github.com/aonpa/Free-Proxy-Checker",
            font=("Segoe UI", 10),
            text_color="#4c4668",
        ).pack(side="bottom", pady=16)

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 20), pady=20)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header_row = ctk.CTkFrame(main, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        ctk.CTkLabel(
            header_row,
            text="Dashboard",
            font=("Segoe UI", 20, "bold"),
            text_color="#e2e8f0",
        ).pack(side="left")
        self.status_chip = ctk.CTkLabel(
            header_row,
            text="  Idle  ",
            font=("Segoe UI", 11),
            text_color=MUTED,
            fg_color=SURFACE,
            corner_radius=20,
        )
        self.status_chip.pack(side="right")

        stats = ctk.CTkFrame(main, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")

        self.stat_loaded = self._stat_card(stats, "Loaded", "0", 0)
        self.stat_valid = self._stat_card(stats, "Valid", "0", 1, SUCCESS)
        self.stat_invalid = self._stat_card(stats, "Invalid", "0", 2, FAIL)
        self.stat_progress = self._stat_card(stats, "Checked", "0%", 3, ACCENT)

        prog_frame = ctk.CTkFrame(main, fg_color=SURFACE, corner_radius=12)
        prog_frame.grid(row=2, column=0, sticky="new", pady=(0, 10))
        prog_frame.grid_columnconfigure(0, weight=1)
        self.progress = SmoothProgressBar(
            prog_frame,
            bar_height=10,
            track_color=BG,
            fill_color=ACCENT,
            canvas_bg=SURFACE,
        )
        self.progress.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        self.progress.set(0)

        log_shell = ctk.CTkFrame(main, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)
        log_shell.grid(row=3, column=0, sticky="nsew")
        log_shell.grid_columnconfigure(0, weight=1)
        log_shell.grid_rowconfigure(1, weight=1)
        main.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            log_shell,
            text="Activity log",
            font=("Segoe UI", 11, "bold"),
            text_color=MUTED,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))

        self.log_box = ctk.CTkTextbox(
            log_shell,
            fg_color=BG,
            border_width=0,
            font=FONT_MONO,
            wrap="none",
            activate_scrollbars=True,
        )
        self.log_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        inner = self.log_box._textbox
        inner.tag_configure("valid", foreground=SUCCESS)
        inner.tag_configure("fail", foreground=FAIL)
        inner.tag_configure("info", foreground=ACCENT)
        inner.tag_configure("muted", foreground=MUTED)
        inner.configure(state="disabled")

    def _stat_card(self, parent, title, value, col, value_color="#e2e8f0"):
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
        card.grid(row=0, column=col, sticky="nsew", padx=4)
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 10), text_color=MUTED).pack(
            anchor="w", padx=14, pady=(12, 0)
        )
        val = ctk.CTkLabel(card, text=value, font=("Segoe UI", 22, "bold"), text_color=value_color)
        val.pack(anchor="w", padx=14, pady=(2, 12))
        return val

    def _create_input(self, label, default):
        frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame.pack(pady=6, padx=20, fill="x")
        ctk.CTkLabel(frame, text=label, text_color=MUTED, font=FONT_UI).pack(anchor="w")
        entry = ctk.CTkEntry(
            frame,
            height=36,
            corner_radius=10,
            fg_color=BG,
            border_color=BORDER,
            font=FONT_UI,
        )
        entry.insert(0, default)
        entry.pack(fill="x", pady=(4, 0))
        return entry

    def _poll_ui(self):
        try:
            while True:
                kind, *payload = self._ui_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload[0], payload[1])
                elif kind == "progress":
                    self._apply_progress(payload[0])
                elif kind == "done":
                    self._on_scan_done()
        except queue.Empty:
            pass
        self._tick_progress_animation()
        self.after(40, self._poll_ui)

    def _tick_progress_animation(self) -> None:
        if abs(self._progress_shown - self._progress_target) < 0.002:
            if self._progress_shown != self._progress_target:
                self._progress_shown = self._progress_target
                self.progress.set(self._progress_shown)
            return
        self._progress_shown += (self._progress_target - self._progress_shown) * 0.22
        self.progress.set(self._progress_shown)

    def _set_status(self, text, color=MUTED):
        self.status_chip.configure(text=f"  {text}  ", text_color=color)

    def _refresh_stat_labels(self):
        total = len(self.proxies)
        valid = len(self.valid_proxies)
        invalid = len(self.invalid_proxies)
        self.stat_loaded.configure(text=str(total))
        self.stat_valid.configure(text=str(valid))
        self.stat_invalid.configure(text=str(invalid))
        if total:
            pct = int(100 * self._checked / total)
            self.stat_progress.configure(text=f"{pct}%")
        else:
            self.stat_progress.configure(text="—")

    def _apply_progress(self, checked):
        self._checked = checked
        total = len(self.proxies) or 1
        self._progress_target = min(1.0, checked / total)
        self._refresh_stat_labels()

    def _reset_progress(self) -> None:
        self._progress_target = 0.0
        self._progress_shown = 0.0
        self.progress.set(0)

    def log(self, msg, tag="info"):
        self._ui_queue.put(("log", msg, tag))

    def _append_log(self, msg, tag="info"):
        inner = self.log_box._textbox
        inner.configure(state="normal")
        inner.insert("1.0", msg + "\n", tag)
        lines = int(inner.index("end-1c").split(".")[0])
        if lines > LOG_MAX_LINES:
            inner.delete(f"{LOG_MAX_LINES + 1}.0", "end")
        inner.configure(state="disabled")

    def load_proxies(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        with open(path, encoding="utf-8") as f:
            self.proxies = [line.strip() for line in f if ":" in line]
        self._checked = 0
        self._reset_progress()
        self._refresh_stat_labels()
        self.log(f"Loaded {len(self.proxies)} proxies from file.", "info")

    def toggle_scan(self):
        if not self.proxies:
            messagebox.showwarning("Free Proxy Checker", "Load a proxy list first.")
            return

        if self.is_running:
            self.is_running = False
            self._set_status("Stopping…", FAIL)
            return

        try:
            threads = int(self.threads_entry.get())
            timeout = int(self.timeout_entry.get())
            if threads < 1 or timeout < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Free Proxy Checker", "Threads and timeout must be positive integers.")
            return

        self.is_running = True
        self.valid_proxies = []
        self.invalid_proxies = []
        self._checked = 0
        self._reset_progress()
        self._refresh_stat_labels()
        self.btn_scan.configure(text="Stop scan", fg_color=DANGER, hover_color=DANGER_HOVER)
        self._set_status("Scanning", ACCENT)
        threading.Thread(target=self.scan, args=(threads, timeout), daemon=True).start()

    def scan(self, threads: int, timeout: int):
        total = len(self.proxies)
        done_counter = {"n": 0}

        def check(proxy):
            if not self.is_running:
                return
            try:
                proxy_url = proxy if "://" in proxy else f"http://{proxy}"
                proxies = {"http": proxy_url, "https": proxy_url}
                start = time.time()
                requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
                ping = int((time.time() - start) * 1000)
                with self._list_lock:
                    self.valid_proxies.append(proxy)
                self.log(f"VALID  {proxy}  ({ping} ms)", "valid")
            except Exception:
                with self._list_lock:
                    self.invalid_proxies.append(proxy)
                self.log(f"FAIL   {proxy}", "fail")
            finally:
                done_counter["n"] += 1
                self._ui_queue.put(("progress", done_counter["n"]))

        with ThreadPoolExecutor(max_workers=threads) as executor:
            list(executor.map(check, self.proxies))

        self._ui_queue.put(("done",))

    def _on_scan_done(self):
        self.is_running = False
        self.btn_scan.configure(
            text="Start scan", fg_color=ACCENT, hover_color=ACCENT_HOVER
        )
        self._set_status("Idle", MUTED)
        self._apply_progress(len(self.proxies))
        self.log("Scan finished.", "muted")

    def export(self, data, name):
        if not data:
            messagebox.showwarning("Free Proxy Checker", "Nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(
            initialfile=f"{name}_Proxies.txt", defaultextension=".txt"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Free Proxy Checker - github.com/aonpa/Free-Proxy-Checker\n")
            f.write("# ----------------------------------------------\n")
            f.write("\n".join(data))
        self.log(f"Exported {len(data)} {name.lower()} proxies.", "info")


if __name__ == "__main__":
    ProxyCheckerApp().mainloop()
