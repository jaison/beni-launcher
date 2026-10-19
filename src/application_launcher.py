"""Tile action normalization and owned application launching."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time

from app_detection import browser_family
from browser_policy import is_safe_web_url
from process_state import owned_process_alive, terminate_owned_process


def resolve_tile_action(tile):
    """Normalize legacy tile commands into one launch action model."""
    command = tile.get("cmd", []) if isinstance(tile, dict) else []
    if not isinstance(command, list):
        return {"type": "none"}
    clean = [part for part in command if isinstance(part, str) and part]
    if clean == ["special:filme-musik"]:
        return {"type": "media"}
    if len(clean) == 1:
        for prefix, mode in (
            ("special:browser:", "embedded"),
            ("special:external-browser:", "external"),
        ):
            if clean[0].startswith(prefix):
                url = clean[0][len(prefix):]
                if not is_safe_web_url(url):
                    raise ValueError("Invalid browser URL")
                return {"type": "web", "mode": mode, "url": url}
    # Older installer versions created browser tiles as `xdg-open URL`.
    if (
        len(clean) == 2
        and clean[0] == "xdg-open"
        and is_safe_web_url(clean[1])
    ):
        return {"type": "web", "mode": "external", "url": clean[1]}
    if len(clean) == 1:
        try:
            clean = shlex.split(clean[0])
        except ValueError:
            clean = []
    return {"type": "app", "argv": clean} if clean else {"type": "none"}


EXTERNAL_PROFILE_SEED = ("extensions", "chrome", "user.js")


def external_firefox_profile(cache_root, profile_id=""):
    """Perfil do Firefox dos sites de cada criança (cookies e logins separados).

    O perfil padrão ("default") continua no diretório antigo; os outros nascem
    com as extensões, o CSS e as preferências do padrão, mas sem cookies/senhas.
    """
    base = os.path.join(os.fspath(cache_root), "external-firefox-profile")
    safe = "".join(ch for ch in (profile_id or "") if ch.isalnum() or ch in "-_")[:64]
    if not safe or safe == "default":
        return base
    path = f"{base}-{safe}"
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        for name in EXTERNAL_PROFILE_SEED:
            source = os.path.join(base, name)
            target = os.path.join(path, name)
            try:
                if os.path.isdir(source):
                    shutil.copytree(source, target)
                elif os.path.isfile(source):
                    shutil.copy2(source, target)
            except OSError:
                pass
    return path


def external_browser_command(browser, url, cache_root, profile_id="", marionette_port=None):
    """Build the isolated kiosk command used for an external web tile."""
    cache_root = os.fspath(cache_root)
    if browser_family(browser) == "chromium":
        profile = os.path.join(cache_root, "external-chromium-profile")
        return [
            browser,
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            "--kiosk",
            f"--app={url}",
        ]
    profile = external_firefox_profile(cache_root, profile_id)
    os.makedirs(profile, exist_ok=True)
    if marionette_port:
        # login automático (site_logins.py): o Marionette só liga neste tile
        _set_user_pref(profile, "marionette.port", int(marionette_port))
        return [browser, "--no-remote", "--profile", profile, "--marionette", "--kiosk", url]
    return [browser, "--no-remote", "--profile", profile, "--kiosk", url]


def _set_user_pref(profile, name, value):
    path = os.path.join(profile, "user.js")
    line = f'user_pref("{name}", {json.dumps(value)});'
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        lines = []
    lines = [item for item in lines if f'"{name}"' not in item] + [line]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def direct_app_command(command):
    """Remove the legacy KDE fullscreen wrapper before supervision."""
    if (
        len(command) >= 3
        and command[0] in ("kstart5", "kstart")
        and command[1] == "--fullscreen"
    ):
        return command[2:]
    return command


class ApplicationLauncher:
    """Start and stop only process trees owned by one launcher tile."""

    def __init__(
        self,
        tile_process_pidfile,
        overlay_pidfile,
        process_supervisor,
        overlay_script,
        activity_file="",
        lock=None,
        python_executable=None,
    ):
        self.tile_process_pidfile = os.fspath(tile_process_pidfile)
        self.overlay_pidfile = os.fspath(overlay_pidfile)
        self.process_supervisor = os.fspath(process_supervisor)
        self.overlay_script = os.fspath(overlay_script)
        self.activity_file = os.fspath(activity_file) if activity_file else ""
        self.lock = lock or threading.Lock()
        self.python_executable = python_executable or sys.executable

    def stop_existing_overlay(self):
        return terminate_owned_process(
            self.overlay_pidfile,
            "overlay",
            self.overlay_script,
        )

    def stop_active_tile(self):
        return terminate_owned_process(
            self.tile_process_pidfile,
            "tile-process",
            self.process_supervisor,
        )

    @staticmethod
    def _wait_for_owned_process(path, role, marker, process, timeout=1.5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if owned_process_alive(path, role, marker):
                return True
            if process.poll() is not None:
                break
            time.sleep(0.05)
        return owned_process_alive(path, role, marker)

    @staticmethod
    def _terminate_started_process(process):
        try:
            process.terminate()
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def start_overlay(self, mode, url="", tile_id=""):
        if not os.path.isfile(self.overlay_script):
            return False
        command = [
            self.python_executable,
            self.overlay_script,
            "--mode",
            mode,
            "--label",
            "Home",
        ]
        if url:
            command.extend(["--url", url])
        if tile_id:
            command.extend(["--tile-id", tile_id])
        process = subprocess.Popen(
            command,
            env=dict(os.environ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self._wait_for_owned_process(
            self.overlay_pidfile,
            "overlay",
            self.overlay_script,
            process,
            timeout=5,
        ):
            return True
        self._terminate_started_process(process)
        return False

    def reset_active_tile(self):
        with self.lock:
            self.stop_existing_overlay()
            self.stop_active_tile()

    def launch_owned_tile(
        self,
        command,
        mode,
        url="",
        tile_id="",
        profile_id="",
        track_activity=False,
    ):
        if not command or not os.path.isfile(self.process_supervisor):
            raise OSError("Tile process supervisor is unavailable")
        with self.lock:
            self.stop_existing_overlay()
            self.stop_active_tile()
            wrapped = [
                self.python_executable,
                self.process_supervisor,
                "--record",
                self.tile_process_pidfile,
                "--marker",
                self.process_supervisor,
            ]
            if track_activity and self.activity_file and profile_id and tile_id:
                wrapped.extend([
                    "--activity-file",
                    self.activity_file,
                    "--activity-profile",
                    profile_id,
                    "--activity-tile",
                    tile_id,
                ])
            wrapped.extend(["--", *command])
            process = subprocess.Popen(
                wrapped,
                env=dict(os.environ),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=(os.name == "posix"),
            )
            if not self._wait_for_owned_process(
                self.tile_process_pidfile,
                "tile-process",
                self.process_supervisor,
                process,
            ):
                self._terminate_started_process(process)
                raise OSError("Tile process ownership could not be established")
            if not self.start_overlay(mode, url=url, tile_id=tile_id):
                self.stop_active_tile()
                raise OSError("Tile overlay could not be started")
            return process
