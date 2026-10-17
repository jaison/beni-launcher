#!/usr/bin/env python3
"""App overlay: always-on-top close button + timer for external browser and local apps."""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
import tkinter as tk
from urllib.parse import quote
from urllib.request import Request, urlopen

from process_state import (
    owned_process,
    owned_process_alive,
    remove_process_record,
    terminate_owned_process,
    write_process_record,
)

HOME = os.path.expanduser("~")
APP_ID = "cozy-kids-launcher"
APP_NAME = "Cozy Kids Launcher"
CACHE_DIR = os.path.join(HOME, ".cache", APP_ID)
BROWSER_PIDFILE = os.path.join(CACHE_DIR, "browser.pid")
TILE_PROCESS_PIDFILE = os.path.join(CACHE_DIR, "tile-process.pid")
OVERLAY_PIDFILE = os.path.join(CACHE_DIR, "overlay.pid")
TILE_PROCESS_MARKER = os.path.join(
    HOME,
    ".local",
    "share",
    APP_ID,
    "process_supervisor.py",
)
OVERLAY_MARKER = os.path.abspath(__file__)

THEME = {
    "bg": "#ffffff",
    "text": "#333333",
    "close_bg": "#ffebee",
    "close_fg": "#c00",
    "timer_text": "#333333",
}


class X11WindowRaiser:
    """Raise one owned X11/XWayland window without a command dependency."""

    def __init__(self, loader=ctypes.CDLL):
        self.library = None
        self.display = None
        if not os.environ.get("DISPLAY"):
            return
        try:
            library = loader("libX11.so.6")
            library.XOpenDisplay.argtypes = [ctypes.c_char_p]
            library.XOpenDisplay.restype = ctypes.c_void_p
            library.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            library.XFlush.argtypes = [ctypes.c_void_p]
            library.XCloseDisplay.argtypes = [ctypes.c_void_p]
            display = library.XOpenDisplay(None)
        except (AttributeError, OSError):
            return
        if display:
            self.library = library
            self.display = display

    def raise_window(self, window_id):
        if not self.library or not self.display:
            return False
        self.library.XRaiseWindow(self.display, ctypes.c_ulong(int(window_id)))
        self.library.XFlush(self.display)
        return True

    def _top_level(self, window_id):
        """Sobe a árvore até a janela filha da raiz (a "wrapper" do Tk)."""
        lib = self.library
        lib.XQueryTree.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint),
        ]
        lib.XFree.argtypes = [ctypes.c_void_p]
        current = int(window_id)
        for _ in range(8):
            root = ctypes.c_ulong()
            parent = ctypes.c_ulong()
            children = ctypes.c_void_p()
            count = ctypes.c_uint()
            if not lib.XQueryTree(self.display, ctypes.c_ulong(current), ctypes.byref(root),
                                  ctypes.byref(parent), ctypes.byref(children), ctypes.byref(count)):
                break
            if children:
                lib.XFree(children)
            if not parent.value or parent.value == root.value:
                break
            current = parent.value
        return current

    def move_window(self, window_id, x, y):
        if not self.library or not self.display:
            return False
        try:
            target = self._top_level(window_id)
        except (AttributeError, OSError):
            target = int(window_id)
        try:
            self.library.XMoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int]
            self.library.XMoveWindow(self.display, ctypes.c_ulong(target), int(x), int(y))
        except AttributeError:
            return False
        self.library.XFlush(self.display)
        return True

    def close(self):
        if self.library and self.display:
            self.library.XCloseDisplay(self.display)
            self.display = None


def configure_overlay_window(window):
    """Apply compositor hints that keep the control above fullscreen apps."""
    try:
        # Tk runs through XWayland in the supported Wayland sessions. KWin can
        # place a plain topmost XWayland window behind an app after that app
        # enters fullscreen. The EWMH dock type keeps this small control on the
        # panel layer without reserving screen space.
        window.attributes("-type", "dock")
    except tk.TclError:
        pass
    try:
        window.attributes("-topmost", True)
    except tk.TclError:
        pass
    window.lift()


def x11_toplevel_id(window):
    """Return the outer X11 frame that the compositor actually stacks."""
    try:
        frame = window.tk.call("wm", "frame", window._w)
        return int(str(frame), 0)
    except (AttributeError, tk.TclError, TypeError, ValueError):
        return int(window.winfo_id())


def api(path, data=None):
    port = os.environ.get("COZY_KIDS_PORT", "38431")
    url = f"http://127.0.0.1:{port}{path}"
    try:
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        else:
            req = Request(url)
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def focus_launcher():
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Cozy Kids Launcher" in line or APP_NAME in line:
                    wid = line.split()[0]
                    subprocess.run(["wmctrl", "-i", "-r", wid, "-b", "add,above"], check=False)
                    subprocess.run(["wmctrl", "-i", "-a", wid], check=False)
                    return
    except Exception:
        pass
    try:
        record = owned_process(BROWSER_PIDFILE, "browser")
        if not record:
            return
        subprocess.run(
            ["xdotool", "search", "--pid", str(record["pid"]), "windowactivate"],
            capture_output=True, timeout=3, check=False,
        )
    except Exception:
        pass


# Faixas de cor do tempo restante (verde -> amarelo -> vermelho).
USAGE_COLORS = {
    "ok": {"bg": "#e8f5e9", "fg": "#1b5e20", "bar": "#43a047"},
    "warn": {"bg": "#fff8e1", "fg": "#7a5200", "bar": "#f9a825"},
    "low": {"bg": "#ffebee", "fg": "#b71c1c", "bar": "#e53935"},
}
COUNTDOWN_SECONDS = 10


def usage_band(remaining, limit):
    if remaining is None:
        return "ok"
    if remaining <= 60:
        return "low"
    if limit:
        fraction = remaining / float(limit)
        if fraction <= 0.2:
            return "low"
        if fraction <= 0.5:
            return "warn"
    return "ok"


def format_remaining(seconds):
    seconds = max(0, int(seconds))
    if seconds >= 60:
        return f"{(seconds + 59) // 60} min"
    return f"{seconds} s"


def tile_is_blocked(status, tile_id):
    if not tile_id or not isinstance(status, dict):
        return False
    blocked = status.get("blockedTileIds", [])
    if not isinstance(blocked, list):
        blocked = []
    return status.get("profileAllowed") is False or tile_id in blocked


class AppOverlay:
    def __init__(self, mode, url, label, tile_id=""):
        self.mode = mode
        self.url = url
        self.label = label
        self.tile_id = tile_id
        self.hide_after_ms = 2000

        self.root = tk.Tk()
        self.root.title("App Overlay")
        self.root.overrideredirect(True)
        self.root.geometry("220x70+24+24")
        self.root.resizable(False, False)
        configure_overlay_window(self.root)
        self.root.focus_force()
        self.x11_raiser = X11WindowRaiser()

        self.frame = tk.Frame(self.root, bg=THEME["bg"], bd=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.close_btn = tk.Button(
            self.frame, text="❌", font=("system-ui", 16, "bold"),
            bg=THEME["close_bg"], fg=THEME["close_fg"], bd=0,
            width=2, height=1, cursor="hand2", command=self.on_close,
        )
        self.close_btn.pack(side=tk.LEFT, padx=8, pady=8)

        self.timer_lbl = tk.Label(
            self.frame, text="", font=("system-ui", 14, "bold"),
            bg=THEME["bg"], fg=THEME["timer_text"],
        )
        self.timer_lbl.pack(side=tk.LEFT, padx=4, pady=8)

        # Bind motion/enter on root, frame, and button for robustness
        for widget in (self.root, self.frame, self.close_btn):
            widget.bind("<Motion>", self.on_motion)
            widget.bind("<Enter>", self.on_motion)

        self.hide_timer = None
        self.reset_hide_timer()

        # Limites diários por categoria
        self.usage_active = None
        self.usage_label = None
        self.countdown_window = None
        self.countdown_deadline = None
        self.countdown_number = None
        self.countdown_geometry = ""
        self.countdown_position = None
        self.closing = False

        self.root.after(0, self.poll_process)
        self.root.after(0, self.poll_timer)
        self.root.after(200, self.poll_usage)
        self.root.after(0, self.stay_on_top)

    def stay_on_top(self):
        """Periodically force this window to the front so it stays visible over kiosk apps."""
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            # Mutter can restack a fullscreen XWayland app above Tk even though
            # Tk still reports the topmost attribute. Raise only this overlay's
            # own XID directly; no global window lookup or extra tool is needed.
            self.x11_raiser.raise_window(x11_toplevel_id(self.root))
            if self.countdown_window is not None:
                # Alguns apps em tela cheia fazem o WM jogar a janela para 0,0.
                # (o Tux Paint, p.ex.) — por isso movemos direto pelo X11.
                self.countdown_window.geometry(self.countdown_geometry)
                if self.countdown_position:
                    window_id = x11_toplevel_id(self.countdown_window)
                    if (self.countdown_window.winfo_rootx(), self.countdown_window.winfo_rooty()) != self.countdown_position:
                        self.x11_raiser.move_window(window_id, *self.countdown_position)
                self.countdown_window.lift()
                self.countdown_window.attributes("-topmost", True)
                self.x11_raiser.raise_window(x11_toplevel_id(self.countdown_window))
        except tk.TclError:
            pass
        self.root.after(500, self.stay_on_top)

    def reset_hide_timer(self):
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
        self.show_full()
        self.hide_timer = self.root.after(self.hide_after_ms, self.show_minimal)

    def show_full(self):
        self.timer_lbl.pack(side=tk.LEFT, padx=4, pady=8)
        self._fit_geometry(70, 220)

    def show_minimal(self):
        # Hide timer label but keep close button visible and fully opaque.
        # Com limite por categoria o tempo restante continua sempre visível.
        if self.usage_label:
            self.timer_lbl.pack(side=tk.LEFT, padx=4, pady=8)
            self._fit_geometry(60, 60)
            return
        self.timer_lbl.pack_forget()
        self.root.geometry("60x60+24+24")

    def _fit_geometry(self, height, minimum):
        try:
            self.root.update_idletasks()
            width = max(minimum, self.frame.winfo_reqwidth() + 8)
        except tk.TclError:
            width = minimum
        self.root.geometry(f"{width}x{height}+24+24")

    # ----- limites por categoria -----
    def poll_usage(self):
        if self.closing:
            return
        path = "/api/usage/status"
        if self.tile_id:
            path += "?tile=" + quote(self.tile_id, safe="")
        data = api(path)
        active = data.get("active") if isinstance(data, dict) and data.get("enabled") else None
        if isinstance(active, dict) and active.get("tileId") == self.tile_id \
                and active.get("remainingSeconds") is not None:
            self.usage_active = active
            remaining = int(active.get("remainingSeconds") or 0)
            self.update_usage_label(active, remaining)
            if remaining <= COUNTDOWN_SECONDS:
                deadline = time.monotonic() + remaining
                if self.countdown_deadline is None or abs(deadline - self.countdown_deadline) > 1.5:
                    self.countdown_deadline = deadline
                if self.countdown_window is None:
                    self.show_countdown(active)
            elif self.countdown_window is not None:
                # Os pais aumentaram o limite: some a contagem.
                self.hide_countdown()
        else:
            self.usage_active = None
            if self.usage_label:
                self.usage_label = None
                self.timer_lbl.config(text="", bg=THEME["bg"])
                self.frame.config(bg=THEME["bg"])
                self.root.config(bg=THEME["bg"])
            if self.countdown_window is not None:
                self.hide_countdown()
        self.root.after(1000, self.poll_usage)

    def update_usage_label(self, active, remaining):
        band = USAGE_COLORS[usage_band(remaining, active.get("limitSeconds"))]
        emoji = active.get("categoryEmoji") or "⏳"
        text = f"{emoji} {format_remaining(remaining)}"
        changed = text != self.usage_label
        self.usage_label = text
        self.timer_lbl.config(text=text, bg=band["bg"], fg=band["fg"], font=("system-ui", 15, "bold"))
        self.frame.config(bg=band["bg"])
        self.root.config(bg=band["bg"])
        if changed and not self.timer_lbl.winfo_ismapped():
            self.show_minimal()
        elif changed:
            self._fit_geometry(self.root.winfo_height() or 60, 60)

    def show_countdown(self, active):
        window = tk.Toplevel(self.root)
        self.countdown_window = window
        window.overrideredirect(True)
        configure_overlay_window(window)
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        ww, wh = min(820, sw - 40), min(440, sh - 40)
        self.countdown_geometry = f"{ww}x{wh}+{(sw - ww) // 2}+{(sh - wh) // 2}"
        window.geometry(self.countdown_geometry)
        self.countdown_position = ((sw - ww) // 2, (sh - wh) // 2)
        border = "#e53935"
        card = "#fffdf7"
        window.configure(bg=border)
        box = tk.Frame(window, bg=card)
        box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        label = (active.get("categoryLabel") or "").strip()
        if active.get("limitedBy") == "category" and label:
            title = f"⏳ Seu tempo de {label.lower()} está acabando!"
        else:
            title = "⏳ Seu tempo de hoje está acabando!"
        tk.Label(box, text=title, font=("system-ui", 26, "bold"), bg=card,
                 fg="#5d4037", wraplength=ww - 60).pack(pady=(26, 0))
        self.countdown_number = tk.Label(box, text="", font=("system-ui", 120, "bold"),
                                         bg=card, fg=border)
        self.countdown_number.pack(expand=True)
        alternatives = [
            alt for alt in active.get("alternatives", [])
            if (alt.get("availableSeconds") or 0) > 0
        ]
        if alternatives:
            parts = [
                f"{alt.get('label', '')} {alt.get('emoji', '')} ({format_remaining(alt.get('availableSeconds'))})"
                for alt in alternatives
            ]
            hint = "Você ainda pode brincar de " + " ou ".join(parts)
            hint_color = "#1b5e20"
        else:
            hint = "Por hoje acabou. Amanhã tem mais! 😊"
            hint_color = "#5d4037"
        tk.Label(box, text=hint, font=("system-ui", 20, "bold"), bg=card,
                 fg=hint_color, wraplength=ww - 60).pack(pady=(0, 28))
        self.tick_countdown()

    def tick_countdown(self):
        if self.countdown_window is None or self.countdown_deadline is None:
            return
        left = self.countdown_deadline - time.monotonic()
        shown = max(0, int(left + 0.999))
        try:
            self.countdown_number.config(text=str(shown) if shown > 0 else "0")
        except tk.TclError:
            return
        if left <= 0:
            self.closing = True
            # Mesmo caminho do ❌: fecha o app e volta para o launcher.
            self.root.after(400, self.on_close)
            return
        self.root.after(200, self.tick_countdown)

    def hide_countdown(self):
        try:
            if self.countdown_window is not None:
                self.countdown_window.destroy()
        except tk.TclError:
            pass
        self.countdown_window = None
        self.countdown_deadline = None
        self.countdown_number = None

    def on_motion(self, event=None):
        self.reset_hide_timer()

    def on_close(self):
        try:
            terminate_owned_process(
                TILE_PROCESS_PIDFILE,
                "tile-process",
                TILE_PROCESS_MARKER,
            )
        except Exception:
            pass
        focus_launcher()
        self.root.destroy()
        sys.exit(0)

    def poll_process(self):
        if not owned_process_alive(
            TILE_PROCESS_PIDFILE,
            "tile-process",
            TILE_PROCESS_MARKER,
        ):
            self.on_close()
            return
        self.root.after(1000, self.poll_process)

    def poll_timer(self):
        availability = api("/api/availability/status")
        if tile_is_blocked(availability, self.tile_id):
            self.on_close()
            return
        data = api("/api/timer/status")
        if self.usage_label:
            pass  # o limite por categoria tem prioridade no rótulo
        elif data.get("active"):
            remaining = data.get("remainingSeconds", 0)
            mins = max(0, remaining // 60)
            if data.get("expired"):
                self.timer_lbl.config(text="⏰ Acabou o tempo!", fg="#c00")
            elif data.get("warning"):
                self.timer_lbl.config(text=f"⏱️ {mins} minutos", fg="#e65100")
            else:
                self.timer_lbl.config(text=f"⏱️ {mins} minutos", fg=THEME["timer_text"])
        else:
            self.timer_lbl.config(text="")
        self.root.after(10000, self.poll_timer)

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.x11_raiser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="external", choices=["external", "local"])
    parser.add_argument("--url", default="")
    parser.add_argument("--label", default="Home")
    parser.add_argument("--tile-id", default="")
    args = parser.parse_args()

    overlay = AppOverlay(args.mode, args.url, args.label, tile_id=args.tile_id)
    write_process_record(
        OVERLAY_PIDFILE,
        os.getpid(),
        "overlay",
        marker=OVERLAY_MARKER,
    )
    try:
        overlay.run()
    finally:
        remove_process_record(OVERLAY_PIDFILE, expected_pid=os.getpid())


if __name__ == "__main__":
    main()
