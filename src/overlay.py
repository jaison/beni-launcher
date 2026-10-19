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
    "ok": {"bg": "#e8f5e9", "fg": "#1b5e20", "bar": "#43a047", "pill_fg": "#86efac"},
    "warn": {"bg": "#fff8e1", "fg": "#7a5200", "bar": "#f9a825", "pill_fg": "#fde047"},
    "low": {"bg": "#ffebee", "fg": "#b71c1c", "bar": "#e53935", "pill_fg": "#fca5a5"},
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


# Visual da barrinha (❌ + tempo): pílula escura, meio transparente.
PILL_BG = "#1f2937"
PILL_ALPHA_IDLE = 0.6
PILL_ALPHA_HOVER = 1.0
PILL_FONT = "Ubuntu"
BUTTON_SIZE = 46
CORNER_MARGIN = 14
CORNERS = ("tl", "tr", "br", "bl")  # ordem do toque em ✥ (sentido horário)
CORNER_FILE = os.path.join(CACHE_DIR, "overlay-corner.json")


def load_corner(tile_id):
    try:
        with open(CORNER_FILE, encoding="utf-8") as handle:
            corner = json.load(handle).get(tile_id or "_", "tl")
    except (OSError, ValueError, AttributeError):
        corner = "tl"
    return corner if corner in CORNERS else "tl"


def save_corner(tile_id, corner):
    try:
        with open(CORNER_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data[tile_id or "_"] = corner
    try:
        with open(CORNER_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
    except OSError:
        pass


def corner_position(corner, width, height, screen_w, screen_h, margin=CORNER_MARGIN):
    x = margin if corner in ("tl", "bl") else screen_w - width - margin
    y = margin if corner in ("tl", "tr") else screen_h - height - margin
    return max(0, x), max(0, y)


def nearest_corner(center_x, center_y, screen_w, screen_h):
    left = center_x < screen_w / 2
    top = center_y < screen_h / 2
    return {(True, True): "tl", (False, True): "tr", (False, False): "br", (True, False): "bl"}[(left, top)]


def process_tree(root_pid):
    """PIDs do processo e de todos os descendentes (lido de /proc)."""
    children = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat", encoding="utf-8") as handle:
                stat = handle.read()
            ppid = int(stat[stat.rindex(")") + 2:].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        children.setdefault(ppid, []).append(int(entry))
    result, pending = [], [int(root_pid)]
    while pending:
        pid = pending.pop()
        result.append(pid)
        pending.extend(children.get(pid, []))
    return result


def rounded_rectangles(width, height, radius):
    """Retângulos (x, y, w, h) que formam um retângulo de cantos redondos."""
    radius = max(0, min(radius, width // 2, height // 2))
    rects = []
    for row in range(radius):
        dy = radius - row - 0.5
        inset = int(round(radius - (radius * radius - dy * dy) ** 0.5))
        rects.append((inset, row, width - 2 * inset, 1))
        rects.append((inset, height - row - 1, width - 2 * inset, 1))
    rects.append((0, radius, width, height - 2 * radius))
    return rects


class _XRectangle(ctypes.Structure):
    _fields_ = [("x", ctypes.c_short), ("y", ctypes.c_short),
                ("width", ctypes.c_ushort), ("height", ctypes.c_ushort)]


def shape_window_rounded(window, width, height, radius):
    """Recorta a janela com cantos redondos (extensão X Shape). Falha em silêncio."""
    try:
        if not os.environ.get("DISPLAY"):
            return False
        xlib = ctypes.CDLL("libX11.so.6")
        xext = ctypes.CDLL("libXext.so.6")
        xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        xlib.XOpenDisplay.restype = ctypes.c_void_p
        xlib.XFlush.argtypes = [ctypes.c_void_p]
        xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
        xext.XShapeCombineRectangles.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(_XRectangle), ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ]
        rects = rounded_rectangles(int(width), int(height), int(radius))
        array = (_XRectangle * len(rects))(*[_XRectangle(*r) for r in rects])
        display = xlib.XOpenDisplay(None)
        if not display:
            return False
        try:
            # ShapeBounding=0, ShapeSet=0, Unsorted=0
            raiser = X11WindowRaiser()
            try:
                target = raiser._top_level(x11_toplevel_id(window)) if raiser.display else x11_toplevel_id(window)
            finally:
                raiser.close()
            xext.XShapeCombineRectangles(display, ctypes.c_ulong(target),
                                         0, 0, 0, array, len(rects), 0, 0)
            xlib.XFlush(display)
        finally:
            xlib.XCloseDisplay(display)
        return True
    except (OSError, AttributeError, tk.TclError, ValueError):
        return False


class RoundButton(tk.Canvas):
    """Botão redondo desenhado num Canvas (o tk.Button não arredonda)."""

    def __init__(self, parent, glyph, fill, fg, hover, command=None, size=BUTTON_SIZE, font_size=20):
        super().__init__(parent, width=size, height=size, bg=PILL_BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.fill, self.hover = fill, hover
        self.oval = self.create_oval(2, 2, size - 2, size - 2, fill=fill, outline="")
        self.create_text(size / 2, size / 2 - 1, text=glyph, fill=fg,
                         font=(PILL_FONT, font_size, "bold"))
        self.command = command
        self.bind("<Enter>", lambda _e: self.itemconfig(self.oval, fill=self.hover), add="+")
        self.bind("<Leave>", lambda _e: self.itemconfig(self.oval, fill=self.fill), add="+")
        if command is not None:
            self.bind("<ButtonRelease-1>", self._release, add="+")

    def _release(self, event):
        # Só conta o clique se o dedo/mouse ainda estiver em cima do botão.
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.command()


class AppOverlay:
    def __init__(self, mode, url, label, tile_id=""):
        self.mode = mode
        self.url = url
        self.label = label
        self.tile_id = tile_id
        self.corner = load_corner(tile_id)
        self.shape_size = None
        self.drag_start = None
        self.dragging = False
        self.idle_job = None

        self.root = tk.Tk()
        self.root.title("App Overlay")
        self.root.overrideredirect(True)
        self.root.configure(bg=PILL_BG)
        self.root.geometry("120x60+14+14")
        self.root.resizable(False, False)
        configure_overlay_window(self.root)
        self.root.focus_force()
        self.x11_raiser = X11WindowRaiser()
        self.set_alpha(PILL_ALPHA_IDLE)

        self.frame = tk.Frame(self.root, bg=PILL_BG, bd=0, padx=6, pady=6)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ‹ Voltar: só em sites (é o Alt+← do navegador), sempre no canto inferior esquerdo
        self.back_window = None
        if mode == "external":
            self.back_window = self.build_back_window()
        self.close_btn = RoundButton(self.frame, "✕", "#ef4444", "#ffffff", "#f87171",
                                     command=self.on_close)
        self.close_btn.pack(side=tk.LEFT, padx=3)

        self.timer_lbl = tk.Label(self.frame, text="", font=(PILL_FONT, 15, "bold"),
                                  bg=PILL_BG, fg="#f9fafb", padx=6)

        self.move_btn = RoundButton(self.frame, "✥", "#374151", "#d1d5db", "#4b5563",
                                    size=34, font_size=16)
        self.move_btn.pack(side=tk.RIGHT, padx=(3, 1))

        # Arrastar pela barra (tempo ou ✥); tocar no ✥ muda de canto.
        for widget in (self.frame, self.timer_lbl, self.move_btn):
            widget.bind("<ButtonPress-1>", self.on_drag_start, add="+")
            widget.bind("<B1-Motion>", self.on_drag_motion, add="+")
            widget.bind("<ButtonRelease-1>", self.on_drag_end, add="+")
        self.root.bind("<Enter>", self.on_enter, add="+")
        self.root.bind("<Leave>", self.on_leave, add="+")

        # Limites diários por categoria
        self.usage_active = None
        self.usage_label = None
        self.countdown_window = None
        self.countdown_deadline = None
        self.countdown_number = None
        self.countdown_geometry = ""
        self.countdown_position = None
        self.closing = False

        self.place()
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
            if self.back_window is not None:
                self.back_window.lift()
                self.back_window.attributes("-topmost", True)
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

    # ----- aparência e posição -----
    def set_alpha(self, value):
        try:
            self.root.attributes("-alpha", value)
        except tk.TclError:
            pass

    def on_enter(self, _event=None):
        if self.idle_job:
            self.root.after_cancel(self.idle_job)
            self.idle_job = None
        self.set_alpha(PILL_ALPHA_HOVER)

    def on_leave(self, _event=None):
        if self.idle_job:
            self.root.after_cancel(self.idle_job)
        self.idle_job = self.root.after(1200, lambda: self.set_alpha(PILL_ALPHA_IDLE))

    def build_back_window(self):
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=PILL_BG)
        configure_overlay_window(window)
        try:
            window.attributes("-alpha", PILL_ALPHA_IDLE)
        except tk.TclError:
            pass
        box = tk.Frame(window, bg=PILL_BG, padx=6, pady=6, cursor="hand2")
        box.pack(fill=tk.BOTH, expand=True)
        arrow = RoundButton(box, "‹", "#e5e7eb", "#111827", "#ffffff", font_size=26)
        arrow.pack(side=tk.LEFT)
        text = tk.Label(box, text="Voltar", font=(PILL_FONT, 15, "bold"), bg=PILL_BG,
                        fg="#f9fafb", padx=8, cursor="hand2")
        text.pack(side=tk.LEFT)

        def release(event):
            widget = event.widget
            if 0 <= event.x <= widget.winfo_width() and 0 <= event.y <= widget.winfo_height():
                self.on_back()

        def alpha(value):
            try:
                window.attributes("-alpha", value)
            except tk.TclError:
                pass

        for widget in (box, arrow, text):
            widget.bind("<ButtonRelease-1>", release, add="+")
        window.bind("<Enter>", lambda _e: alpha(PILL_ALPHA_HOVER), add="+")
        window.bind("<Leave>", lambda _e: window.after(1200, lambda: alpha(PILL_ALPHA_IDLE)), add="+")
        window.update_idletasks()
        width, height = box.winfo_reqwidth(), box.winfo_reqheight()
        x, y = corner_position("bl", width, height, window.winfo_screenwidth(), window.winfo_screenheight())
        window.geometry(f"{width}x{height}+{x}+{y}")
        self.back_height = height
        window.update_idletasks()
        shape_window_rounded(window, width, height, height // 2)
        return window

    def size(self):
        try:
            self.root.update_idletasks()
            return self.frame.winfo_reqwidth(), self.frame.winfo_reqheight()
        except tk.TclError:
            return 120, 60

    def place(self):
        width, height = self.size()
        x, y = corner_position(self.corner, width, height,
                               self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        if self.corner == "bl" and self.back_window is not None:
            y -= self.back_height + 10  # fica logo acima do ‹ Voltar
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        if self.shape_size != (width, height):
            self.root.update_idletasks()
            if shape_window_rounded(self.root, width, height, height // 2):
                self.shape_size = (width, height)

    def set_timer_text(self, text, fg="#f9fafb"):
        if text:
            self.timer_lbl.config(text=text, fg=fg)
            if not self.timer_lbl.winfo_ismapped():
                self.timer_lbl.pack(side=tk.LEFT, padx=(4, 2))
        else:
            self.timer_lbl.config(text="")
            self.timer_lbl.pack_forget()
        self.place()

    def on_drag_start(self, event):
        self.drag_start = (event.x_root, event.y_root,
                           self.root.winfo_rootx(), self.root.winfo_rooty())
        self.dragging = False

    def on_drag_motion(self, event):
        if not self.drag_start:
            return
        sx, sy, wx, wy = self.drag_start
        dx, dy = event.x_root - sx, event.y_root - sy
        if not self.dragging and abs(dx) + abs(dy) < 10:
            return
        self.dragging = True
        self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def on_drag_end(self, event):
        if not self.drag_start:
            return
        if self.dragging:
            width, height = self.size()
            self.corner = nearest_corner(self.root.winfo_rootx() + width / 2,
                                         self.root.winfo_rooty() + height / 2,
                                         self.root.winfo_screenwidth(),
                                         self.root.winfo_screenheight())
        elif event.widget is self.move_btn:
            self.corner = CORNERS[(CORNERS.index(self.corner) + 1) % len(CORNERS)]
        else:
            self.drag_start = None
            return
        self.drag_start = None
        self.dragging = False
        save_corner(self.tile_id, self.corner)
        self.place()

    def on_back(self):
        """Volta uma página no navegador do tile (Alt+←)."""
        record = owned_process(TILE_PROCESS_PIDFILE, "tile-process")
        if not record:
            return
        windows = []
        try:
            for pid in process_tree(record["pid"]):
                found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(pid)],
                                       capture_output=True, text=True, timeout=2)
                windows.extend(found.stdout.split())
        except (OSError, subprocess.SubprocessError):
            return
        if not windows:
            return
        try:
            subprocess.run(["xdotool", "windowactivate", "--sync", windows[0],
                            "key", "--clearmodifiers", "alt+Left"],
                           capture_output=True, timeout=3, check=False)
        except (OSError, subprocess.SubprocessError):
            pass

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
                self.set_timer_text("")
            if self.countdown_window is not None:
                self.hide_countdown()
        self.root.after(1000, self.poll_usage)

    def update_usage_label(self, active, remaining):
        band = USAGE_COLORS[usage_band(remaining, active.get("limitSeconds"))]
        emoji = active.get("categoryEmoji") or "⏳"
        text = f"{emoji} {format_remaining(remaining)}"
        if text != self.usage_label:
            self.usage_label = text
            self.set_timer_text(text, band["pill_fg"])

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
                self.set_timer_text("⏰ Acabou!", "#fca5a5")
            elif data.get("warning"):
                self.set_timer_text(f"⏱️ {mins} min", "#fde047")
            else:
                self.set_timer_text(f"⏱️ {mins} min")
        elif self.timer_lbl.cget("text"):
            self.set_timer_text("")
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
