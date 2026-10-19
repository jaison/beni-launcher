"""Login automático em sites (Khan Academy, Teach Your Monster), por perfil.

O e-mail e a senha ficam em ~/.config/cozy-kids-launcher/site-logins.json
(permissão 600), fora do config.json, e a senha nunca volta para a página:
a área dos pais só vê o e-mail e se há senha salva.

Ao abrir o site, o Firefox sobe com o Marionette (o controle remoto do próprio
Firefox) só para esse tile; uma thread preenche a página de login do site e
clica em "Entrar". Se a sessão ainda estiver aberta (cookie), nada é digitado.
"""

import json
import os
import socket
import tempfile
import threading
import time
from urllib.parse import quote, urlparse

MARIONETTE_PORT = 28290

SITES = {
    "khan": {
        "label": "Khan Academy",
        "hosts": ("khanacademy.org",),
        "login_url": "https://pt.khanacademy.org/login",
        "user_selector": "[data-testid=identifier-field]",
        "password_selector": "[data-testid=password-field]",
        "submit_selector": "[data-testid=log-in-submit-button]",
        # aviso de cookies (TrustArc): "Somente os necessários"
        "dismiss_selectors": ("#truste-consent-required",),
        "continue_param": "continue",
    },
    "teachyourmonster": {
        "label": "Teach Your Monster",
        "hosts": ("teachyourmonster.org",),
        "login_url": "https://www.teachyourmonster.org/account/users/sign_in",
        # conta de família: aba "Home" (as outras são Student e Teacher)
        "pre_click_selectors": ("#tab_home",),
        "user_selector": "form.user.home input[name='oog_user[email]']",
        "password_selector": "form.user.home input[name='oog_user[password]']",
        "submit_selector": "form.user.home button[type=submit]",
        "dismiss_selectors": (),
    },
}

MAX_FIELD = 200


# ------------------------------------------------------------ armazenamento

def _empty():
    return {"version": 1, "profiles": {}}


def load_logins(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return _empty()
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        return _empty()
    return data


def save_logins(path, data):
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".site-logins.", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get_login(path, profile_id, site):
    entry = load_logins(path)["profiles"].get(profile_id, {}).get(site)
    if not isinstance(entry, dict) or not entry.get("username") or not entry.get("password"):
        return None
    return entry


def public_logins(path, profile_id):
    """O que a área dos pais pode ver: e-mail e se há senha (nunca a senha)."""
    stored = load_logins(path)["profiles"].get(profile_id, {})
    result = []
    for site, info in SITES.items():
        entry = stored.get(site) if isinstance(stored.get(site), dict) else {}
        result.append({
            "id": site,
            "label": info["label"],
            "username": entry.get("username", ""),
            "hasPassword": bool(entry.get("password")),
        })
    return result


def update_login(path, profile_id, site, username=None, password=None, remove=False):
    """Grava/apaga o login. password=None mantém a senha já salva."""
    if site not in SITES:
        raise ValueError("unknown site")
    if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 64:
        raise ValueError("invalid profile")
    data = load_logins(path)
    profiles = data["profiles"]
    if remove:
        profiles.get(profile_id, {}).pop(site, None)
        if not profiles.get(profile_id):
            profiles.pop(profile_id, None)
        save_logins(path, data)
        return
    for value in (username, password):
        if value is not None and (not isinstance(value, str) or len(value) > MAX_FIELD):
            raise ValueError("invalid field")
    username = (username or "").strip()
    if not username:
        raise ValueError("username required")
    entry = profiles.setdefault(profile_id, {}).setdefault(site, {})
    entry["username"] = username
    if password:
        entry["password"] = password
    if not entry.get("password"):
        raise ValueError("password required")
    save_logins(path, data)


def site_for_url(url):
    host = (urlparse(url).hostname or "").lower()
    for site, info in SITES.items():
        if any(host == h or host.endswith("." + h) for h in info["hosts"]):
            return site
    return None


# ------------------------------------------------------------- Marionette

class Marionette:
    """Cliente mínimo do protocolo Marionette do Firefox (só stdlib)."""

    def __init__(self, port, host="127.0.0.1", connect_timeout=40, io_timeout=60):
        deadline = time.time() + connect_timeout
        while True:
            try:
                self.sock = socket.create_connection((host, port), timeout=io_timeout)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.4)
        self.buf = b""
        self.msg_id = 0
        self._read()  # mensagem de boas-vindas

    def _read(self):
        while b":" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("marionette closed")
            self.buf += chunk
        size, rest = self.buf.split(b":", 1)
        size = int(size)
        while len(rest) < size:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("marionette closed")
            rest += chunk
        self.buf = rest[size:]
        return json.loads(rest[:size])

    def cmd(self, name, params=None):
        self.msg_id += 1
        data = json.dumps([0, self.msg_id, name, params or {}]).encode()
        self.sock.sendall(str(len(data)).encode() + b":" + data)
        while True:
            msg = self._read()
            if msg[0] == 1 and msg[1] == self.msg_id:
                if msg[2]:
                    raise RuntimeError(msg[2].get("error", "marionette error"))
                return msg[3]

    def script(self, source, *args):
        return self.cmd("WebDriver:ExecuteScript", {"script": source, "args": list(args)}).get("value")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


_FILL_SCRIPT = """
const [user, pass, userSel, passSel, submitSel, dismiss, preClick] = arguments;
for (const sel of dismiss) { const b = document.querySelector(sel); if (b && b.offsetParent) b.click(); }
for (const sel of preClick) { const b = document.querySelector(sel); if (b) b.click(); }
const u = document.querySelector(userSel), p = document.querySelector(passSel), s = document.querySelector(submitSel);
if (!u || !p || !s) return 'wait';
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
for (const [el, v] of [[u, user], [p, pass]]) {
  setter.call(el, v);
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
}
s.click();
return 'sent';
"""


def auto_login(site, username, password, target_url, port=MARIONETTE_PORT, log=None, timeout=60):
    """Faz o login no Firefox recém-aberto. Devolve 'ok', 'already', 'failed' ou 'error'."""
    info = SITES[site]
    log = log or (lambda *a, **k: None)
    client = None
    try:
        client = Marionette(port)
        client.cmd("WebDriver:NewSession", {"capabilities": {"pageLoadStrategy": "eager"}})
        login_path = urlparse(info["login_url"]).path
        target_path = urlparse(target_url).path or "/"
        login_url = info["login_url"]
        if info.get("continue_param"):
            login_url += "?" + info["continue_param"] + "=" + quote(target_path, safe="/")
        client.cmd("WebDriver:Navigate", {"url": login_url})
        deadline = time.time() + timeout
        sent = False
        while time.time() < deadline:
            here = urlparse(client.script("return location.href") or "")
            if not here.path.startswith(login_path):
                result = "ok" if sent else "already"
                break
            if not sent:
                if client.script(
                    _FILL_SCRIPT, username, password, info["user_selector"],
                    info["password_selector"], info["submit_selector"],
                    list(info.get("dismiss_selectors", ())), list(info.get("pre_click_selectors", ())),
                ) == "sent":
                    sent = True
                    sent_at = time.time()
            elif time.time() - sent_at > 15:
                result = "failed"   # continua na página de login (senha errada?)
                break
            time.sleep(0.7)
        else:
            result = "failed"
        if result in ("ok", "already"):
            # depois do login, vai para a página do tile (se o site não foi sozinho)
            if urlparse(client.script("return location.href") or "").path.rstrip("/") != target_path.rstrip("/"):
                client.cmd("WebDriver:Navigate", {"url": target_url})
        log("site_login.finished", result={"ok": "success", "already": "already"}.get(result, "failure"))
        return result
    except Exception as exc:  # noqa: BLE001 — nunca derruba o launcher
        log("site_login.finished", level="warning", result="failure", exceptionType=type(exc).__name__)
        return "error"
    finally:
        if client is not None:
            try:
                client.cmd("WebDriver:DeleteSession")
            except Exception:  # noqa: BLE001
                pass
            client.close()


def start_auto_login(site, username, password, target_url, log=None):
    thread = threading.Thread(
        target=auto_login,
        args=(site, username, password, target_url),
        kwargs={"log": log},
        name=f"site-login-{site}",
        daemon=True,
    )
    thread.start()
    return thread
