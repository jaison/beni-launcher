"""Limites diários de uso por categoria (ex.: Jogos 30 min + Aprender 30 min).

Uma categoria pode dividir o limite de outra ("pool": "jogos"): o Passatempo,
por exemplo, gasta dos mesmos 30 min dos Jogos.

O tempo só conta enquanto um app/site lançado pelo launcher está aberto.
O uso acumula por dia (data local; zera à meia-noite) e por perfil, e fica
persistido em ~/.local/state/cozy-kids-launcher/usage-today.json para
sobreviver a reinícios do servidor.
"""

import copy
import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime


USAGE_VERSION = 1
CATEGORY_ID_PATTERN = re.compile(r"[a-z0-9_-]{1,32}")
MAX_CATEGORIES = 12
MAX_LIMIT_MINUTES = 24 * 60
SAVE_INTERVAL_SECONDS = 5.0
# Margem antes de o servidor fechar o app sozinho, caso o overlay não o faça.
ENFORCE_GRACE_SECONDS = 3

# Categorias conhecidas. Outras podem ser criadas no config.json com
# label/emoji próprios em categoryLimits.categories.
BUILTIN_CATEGORIES = {
    "jogos": {"label": "Jogos", "emoji": "🎮"},
    "educativo": {"label": "Aprender", "emoji": "📚"},
    "passatempo": {"label": "Passatempo", "emoji": "🎨"},
}

DEFAULT_CATEGORY_LIMITS = {
    "enabled": True,
    "totalMinutes": 60,
    "categories": {
        "jogos": {"minutes": 30},
        "educativo": {"minutes": 30},
        "passatempo": {"minutes": None, "pool": "jogos"},
    },
}

_EDUCATIVO_IDS = {
    "scratch", "blockly", "klavaro", "codeorg", "khan",
    "phet", "stellarium", "browser", "tuxmath",
}
_PASSATEMPO_IDS = {
    "paint", "autodraw", "colorir", "games", "musiclab", "klotski", "hexahop", "pingus",
}
_JOGOS_IDS = {
    "luanti", "supertux", "supertuxkart", "snes", "ps1", "frogatto",
    "music", "youtube-kids", "netflix-kids", "disney-plus", "prime-kids",
    "pbs-kids", "zdf-tivi", "kika",
}


def default_category_for_tile(tile):
    """Categoria sugerida para um tile sem categoria ("" = sem categoria).

    Aceita o dict do tile ou só o id. Jogos de navegador abertos pelo
    wrapper navegador-jogos/cozy-jogos contam como "jogos".
    """
    tile_id = tile.get("id", "") if isinstance(tile, dict) else str(tile)
    command = tile.get("cmd", []) if isinstance(tile, dict) else []
    first = os.path.basename(command[0]) if command and isinstance(command[0], str) else ""
    if tile_id in _EDUCATIVO_IDS:
        return "educativo"
    if tile_id in _PASSATEMPO_IDS:
        return "passatempo"
    if (
        tile_id in _JOGOS_IDS
        or tile_id.startswith("rb-")
        or first in ("navegador-jogos", "cozy-jogos")
    ):
        return "jogos"
    return ""


def effective_tile_category(tile):
    """Categoria gravada no tile; sem o campo, usa a sugestão padrão."""
    if "category" in tile:
        return tile.get("category") or ""
    return default_category_for_tile(tile)


# ---------------------------------------------------------------- validação

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _minutes(value, field, allow_none=True):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_LIMIT_MINUTES:
        raise ValueError(f"{field} must be between 0 and {MAX_LIMIT_MINUTES} minutes")
    return value


def validate_tile_category(value, field):
    if value == "":
        return ""
    if not isinstance(value, str) or not CATEGORY_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a short lowercase category id")
    return value


def _validate_weekdays(value, categories, field):
    """{mon..sun: {totalMinutes?, categories?: {id: minutes}}}.

    Campo ausente no dia = usa o valor padrão; null = sem limite nesse dia.
    """
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    clean = {}
    for day, entry in value.items():
        if day not in WEEKDAYS:
            raise ValueError(f"{field} contains an invalid weekday")
        if not isinstance(entry, dict) or set(entry).difference(("totalMinutes", "categories")):
            raise ValueError(f"{field}.{day} must be an object")
        item = {}
        if "totalMinutes" in entry:
            item["totalMinutes"] = _minutes(entry["totalMinutes"], f"{field}.{day}.totalMinutes")
        cats = entry.get("categories", {})
        if not isinstance(cats, dict):
            raise ValueError(f"{field}.{day}.categories must be an object")
        day_cats = {}
        for category_id, minutes in cats.items():
            if category_id not in categories:
                continue  # categoria removida: ignora
            if isinstance(minutes, dict):
                minutes = minutes.get("minutes")
            day_cats[category_id] = _minutes(minutes, f"{field}.{day}.categories.{category_id}")
        if day_cats:
            item["categories"] = day_cats
        clean[day] = item
    return clean


def weekday_key(now=None):
    moment = datetime.fromtimestamp(time.time() if now is None else now).astimezone()
    return WEEKDAYS[moment.weekday()]


def limits_for_day(limits, day):
    """Limites que valem no dia (aplica categoryLimits.weekdays[day] sobre o padrão)."""
    limits = limits or {}
    override = (limits.get("weekdays") or {}).get(day)
    if not override:
        return limits
    result = copy.deepcopy(limits)
    if "totalMinutes" in override:
        result["totalMinutes"] = override["totalMinutes"]
    for category_id, minutes in (override.get("categories") or {}).items():
        if category_id in result.get("categories", {}):
            result["categories"][category_id]["minutes"] = minutes
    return result


def validate_category_limits(value, field="categoryLimits"):
    """Normaliza {enabled,totalMinutes,categories:{id:{minutes,label?,emoji?}},weekdays?}."""
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    unknown = set(value).difference(("enabled", "totalMinutes", "categories", "weekdays"))
    if unknown:
        raise ValueError(f"{field} contains unsupported fields")
    enabled = value.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError(f"{field}.enabled must be a boolean")
    total = _minutes(value.get("totalMinutes"), f"{field}.totalMinutes")
    categories = value.get("categories", {})
    if not isinstance(categories, dict) or len(categories) > MAX_CATEGORIES:
        raise ValueError(f"{field}.categories must be a small object")
    clean = {}
    for category_id, entry in categories.items():
        if not isinstance(category_id, str) or not CATEGORY_ID_PATTERN.fullmatch(category_id):
            raise ValueError(f"{field}.categories contains an invalid id")
        if isinstance(entry, int) and not isinstance(entry, bool):
            entry = {"minutes": entry}
        if not isinstance(entry, dict):
            raise ValueError(f"{field}.categories.{category_id} must be an object")
        extra = set(entry).difference(("minutes", "label", "emoji", "pool"))
        if extra:
            raise ValueError(f"{field}.categories.{category_id} has unsupported fields")
        item = {"minutes": _minutes(entry.get("minutes"), f"{field}.categories.{category_id}.minutes")}
        for key, maximum in (("label", 40), ("emoji", 16)):
            if key in entry:
                text = entry[key]
                if not isinstance(text, str) or len(text) > maximum:
                    raise ValueError(f"{field}.categories.{category_id}.{key} is invalid")
                item[key] = text
        if entry.get("pool") not in (None, "", category_id):
            pool = entry["pool"]
            if not isinstance(pool, str) or not CATEGORY_ID_PATTERN.fullmatch(pool):
                raise ValueError(f"{field}.categories.{category_id}.pool is invalid")
            item["pool"] = pool
        clean[category_id] = item
    # o pool tem que apontar para uma categoria que existe e que não divide com outra
    for category_id, item in clean.items():
        pool = item.get("pool")
        if pool and (pool not in clean or clean[pool].get("pool")):
            del item["pool"]
    result = {"enabled": enabled, "totalMinutes": total, "categories": clean}
    if value.get("weekdays"):
        result["weekdays"] = _validate_weekdays(value["weekdays"], clean, f"{field}.weekdays")
    return result


# ------------------------------------------------------------- persistência

def today_key(now=None):
    moment = datetime.fromtimestamp(time.time() if now is None else now).astimezone()
    return moment.strftime("%Y-%m-%d")


def _empty_usage(day):
    return {"usageVersion": USAGE_VERSION, "date": day, "profiles": {}}


def load_usage(path, now=None):
    day = today_key(now)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return _empty_usage(day)
    if (
        not isinstance(data, dict)
        or data.get("usageVersion") != USAGE_VERSION
        or data.get("date") != day
        or not isinstance(data.get("profiles"), dict)
    ):
        return _empty_usage(day)
    profiles = {}
    for profile_id, entry in data["profiles"].items():
        if not isinstance(profile_id, str) or not isinstance(entry, dict):
            continue
        total = entry.get("totalSeconds", 0)
        cats = entry.get("categories", {})
        if not isinstance(total, (int, float)) or not isinstance(cats, dict):
            continue
        profiles[profile_id] = {
            "totalSeconds": max(0.0, float(total)),
            "categories": {
                str(k): max(0.0, float(v))
                for k, v in cats.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            },
        }
    return {"usageVersion": USAGE_VERSION, "date": day, "profiles": profiles}


def save_usage(path, data):
    directory = os.path.dirname(os.fspath(path)) or "."
    os.makedirs(directory, mode=0o700, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="usage-", suffix=".json", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# ------------------------------------------------------------------ cálculo

def category_pool(limits, category_id):
    """Categoria dona do limite: a própria ou a indicada em "pool"."""
    categories = (limits or {}).get("categories", {})
    pool = (categories.get(category_id) or {}).get("pool")
    return pool if pool in categories else category_id


def category_definitions(limits):
    """Lista ordenada de categorias configuradas, com nome, emoji e pool.

    "minutes" é o limite que vale para a categoria (o do pool, se dividir).
    """
    result = []
    categories = (limits or {}).get("categories", {})
    for category_id, entry in categories.items():
        builtin = BUILTIN_CATEGORIES.get(category_id, {})
        pool = category_pool(limits, category_id)
        result.append({
            "id": category_id,
            "label": entry.get("label") or builtin.get("label") or category_id.capitalize(),
            "emoji": entry.get("emoji") or builtin.get("emoji") or "⭐",
            "minutes": (categories.get(pool) or {}).get("minutes"),
            "pool": pool,
        })
    return result


def pooled_seconds(limits, usage_categories, pool):
    """Segundos usados por todas as categorias que dividem o limite `pool`."""
    return sum(
        seconds for category_id, seconds in (usage_categories or {}).items()
        if category_pool(limits, category_id) == pool
    )


def tile_category(profile, tile_id):
    for tile in profile.get("tiles", []):
        if tile.get("id") == tile_id:
            return effective_tile_category(tile)
    return ""


def _remaining(limit_minutes, used_seconds):
    if limit_minutes is None:
        return None
    return int(limit_minutes * 60 - used_seconds)


def compute_status(profile, usage_entry, active=None, now=None):
    """Retorna o payload público de uso para um perfil (limites do dia de hoje)."""
    day = weekday_key(now)
    base_limits = profile.get("categoryLimits") or {}
    limits = limits_for_day(base_limits, day)
    enabled = bool(limits.get("enabled"))
    usage_entry = usage_entry or {"totalSeconds": 0.0, "categories": {}}
    used_total = usage_entry.get("totalSeconds", 0.0)
    total_limit = limits.get("totalMinutes") if enabled else None
    total_remaining = _remaining(total_limit, used_total)
    total_exhausted = enabled and total_remaining is not None and total_remaining <= 0

    categories = []
    exhausted_ids = set()
    for definition in category_definitions(limits):
        used = usage_entry.get("categories", {}).get(definition["id"], 0.0)
        pool_used = pooled_seconds(limits, usage_entry.get("categories", {}), definition["pool"])
        own_remaining = _remaining(definition["minutes"], pool_used) if enabled else None
        effective = own_remaining
        if total_remaining is not None:
            effective = total_remaining if effective is None else min(effective, total_remaining)
        exhausted = enabled and effective is not None and effective <= 0
        if exhausted:
            exhausted_ids.add(definition["id"])
        categories.append({
            **definition,
            "usedSeconds": int(used),
            "poolUsedSeconds": int(pool_used),
            "remainingSeconds": None if own_remaining is None else max(0, own_remaining),
            "availableSeconds": None if effective is None else max(0, effective),
            "exhausted": exhausted,
        })

    blocked = []
    reasons = {}
    if enabled:
        for tile in profile.get("tiles", []):
            tile_id = tile.get("id")
            if not tile_id:
                continue
            if total_exhausted:
                blocked.append(tile_id)
                reasons[tile_id] = "daily_limit"
            elif effective_tile_category(tile) in exhausted_ids:
                blocked.append(tile_id)
                reasons[tile_id] = "category_limit"

    active_payload = None
    if active:
        category_id = active.get("category", "")
        cat = next((c for c in categories if c["id"] == category_id), None)
        own = cat["remainingSeconds"] if cat else None
        remaining = None
        limited_by = ""
        if enabled:
            if own is not None and (total_remaining is None or own <= total_remaining):
                remaining, limited_by = own, "category"
            elif total_remaining is not None:
                remaining, limited_by = max(0, total_remaining), "total"
        alternatives = []
        if enabled and limited_by == "category":
            own_pool = cat["pool"] if cat else category_id
            for other in categories:
                if other["id"] == category_id or other["exhausted"] or other["pool"] == own_pool:
                    continue
                alternatives.append({
                    "id": other["id"],
                    "label": other["label"],
                    "emoji": other["emoji"],
                    "availableSeconds": other["availableSeconds"],
                })
        active_payload = {
            "tileId": active.get("tileId", ""),
            "category": category_id,
            "categoryLabel": cat["label"] if cat else "",
            "categoryEmoji": cat["emoji"] if cat else "⏳",
            "limitSeconds": (
                (cat["minutes"] * 60 if cat and cat["minutes"] is not None else None)
                if limited_by == "category"
                else (total_limit * 60 if total_limit is not None else None)
            ),
            "remainingSeconds": remaining,
            "limitedBy": limited_by,
            "alternatives": alternatives,
        }

    return {
        "enabled": enabled,
        "weekday": day,
        "weekdayLimits": bool(base_limits.get("weekdays")),
        "totalMinutes": total_limit,
        "totalUsedSeconds": int(used_total),
        "totalRemainingSeconds": None if total_remaining is None else max(0, total_remaining),
        "totalExhausted": total_exhausted,
        "categories": categories,
        "blockedTileIds": blocked,
        "blockedReasons": reasons,
        # Categoria efetiva de cada tile (inclui a regra padrão para tiles
        # sem o campo "category"); usada pela tela de escolha Aprender/Jogar.
        "tileCategories": {
            tile.get("id"): effective_tile_category(tile)
            for tile in profile.get("tiles", [])
            if tile.get("id")
        },
        "active": active_payload,
    }


# ----------------------------------------------------------------- tracker

class UsageTracker:
    """Acumula segundos de uso do tile ativo e aplica os limites.

    load_profiles(): devolve (dict profile_id -> perfil armazenado).
    tile_alive(): True enquanto o processo do tile está aberto.
    stop_tile(): fecha o app aberto (mesmo efeito do ❌).
    """

    def __init__(self, path, load_profiles, tile_alive, stop_tile, clock=time.time):
        self.path = os.fspath(path)
        self.load_profiles = load_profiles
        self.tile_alive = tile_alive
        self.stop_tile = stop_tile
        self.clock = clock
        self.lock = threading.RLock()
        self.usage = load_usage(self.path)
        self.active = None
        self.last_tick = None
        self.last_save = 0.0
        self.dirty = False
        self.last_expiry = None
        self._thread = None
        self._stop = threading.Event()

    # -- ciclo de vida
    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="usage-tracker", daemon=True)
            self._thread.start()

    def shutdown(self):
        self._stop.set()
        with self.lock:
            self._accrue()
            self._save(force=True)

    def _run(self):
        while not self._stop.wait(1.0):
            try:
                self.tick()
            except Exception:
                pass

    # -- tile ativo
    def set_active(self, profile_id, tile_id, category):
        with self.lock:
            self._accrue()
            self.active = {
                "profileId": profile_id,
                "tileId": tile_id,
                "category": category or "",
                "startedAt": self.clock(),
            }
            self.last_tick = self.clock()

    def adopt(self, profile_id, tile_id, category, tile_alive):
        """Retoma um tile que ainda está aberto (ex.: após reiniciar o servidor)."""
        with self.lock:
            if self.active is None and tile_alive():
                self.set_active(profile_id, tile_id, category)

    def clear_active(self):
        with self.lock:
            self._accrue()
            self.active = None
            self.last_tick = None
            self._save(force=True)

    # -- contagem
    def _roll_day(self):
        day = today_key(self.clock())
        if self.usage.get("date") != day:
            self.usage = _empty_usage(day)
            self.last_expiry = None
            self.dirty = True

    def _entry(self, profile_id):
        return self.usage["profiles"].setdefault(
            profile_id, {"totalSeconds": 0.0, "categories": {}}
        )

    def _accrue(self):
        now = self.clock()
        self._roll_day()
        if self.active and self.last_tick is not None:
            delta = now - self.last_tick
            # Ignora saltos (suspensão do notebook, relógio ajustado).
            if 0 < delta <= 10:
                entry = self._entry(self.active["profileId"])
                entry["totalSeconds"] += delta
                category = self.active.get("category")
                if category:
                    entry["categories"][category] = entry["categories"].get(category, 0.0) + delta
                self.dirty = True
        self.last_tick = now if self.active else None

    def _save(self, force=False):
        now = self.clock()
        if self.dirty and (force or now - self.last_save >= SAVE_INTERVAL_SECONDS):
            try:
                save_usage(self.path, self.usage)
                self.dirty = False
                self.last_save = now
            except OSError:
                pass

    def tick(self):
        stop_needed = False
        with self.lock:
            if self.active and not self.tile_alive():
                self._accrue()
                self.active = None
                self.last_tick = None
                self._save(force=True)
                return
            self._accrue()
            if self.active:
                profile = self.load_profiles().get(self.active["profileId"])
                if profile:
                    status = compute_status(profile, self.usage["profiles"].get(self.active["profileId"]), self.active, now=self.clock())
                    remaining = (status.get("active") or {}).get("remainingSeconds")
                    if remaining is not None and remaining <= 0:
                        self._remember_expiry(status)
                        self._save(force=True)
                        # Contamos a partir do instante em que zerou (o overlay
                        # fecha o app no 0; aqui é só a garantia).
                        used_over = self._overrun(profile)
                        if used_over >= ENFORCE_GRACE_SECONDS:
                            stop_needed = True
            self._save()
        if stop_needed:
            try:
                self.stop_tile()
            finally:
                self.clear_active()

    def _overrun(self, profile):
        """Segundos além do limite consumidos pelo app ativo."""
        entry = self.usage["profiles"].get(self.active["profileId"], {})
        limits = limits_for_day(profile.get("categoryLimits"), weekday_key(self.clock()))
        overs = []
        total = limits.get("totalMinutes")
        if total is not None:
            overs.append(entry.get("totalSeconds", 0) - total * 60)
        category = self.active.get("category")
        pool = category_pool(limits, category) if category else None
        cat_limit = (limits.get("categories", {}).get(pool) or {}).get("minutes") if pool else None
        if cat_limit is not None:
            overs.append(pooled_seconds(limits, entry.get("categories", {}), pool) - cat_limit * 60)
        return max(overs) if overs else 0

    def _remember_expiry(self, status):
        active = status.get("active") or {}
        if self.last_expiry and self.last_expiry.get("tileId") == active.get("tileId") \
                and self.clock() - self.last_expiry.get("at", 0) < 60:
            return
        self.last_expiry = {
            "at": int(self.clock()),
            "profileId": self.active["profileId"],
            "tileId": active.get("tileId", ""),
            "category": active.get("category", ""),
            "categoryLabel": active.get("categoryLabel", ""),
            "categoryEmoji": active.get("categoryEmoji", ""),
            "limitedBy": active.get("limitedBy", ""),
        }

    # -- consulta
    def status(self, profile_id, profile):
        with self.lock:
            self._accrue()
            active = self.active if self.active and self.active["profileId"] == profile_id else None
            payload = compute_status(profile, self.usage["profiles"].get(profile_id), active, now=self.clock())
            payload["date"] = self.usage["date"]
            payload["profileId"] = profile_id
            payload["now"] = int(self.clock())
            if self.last_expiry and self.last_expiry.get("profileId") == profile_id:
                payload["lastExpiry"] = copy.deepcopy(self.last_expiry)
            return payload

    def reset(self, profile_id=None):
        with self.lock:
            self._accrue()
            if profile_id:
                self.usage["profiles"].pop(profile_id, None)
            else:
                self.usage["profiles"] = {}
            self.last_expiry = None
            self.dirty = True
            self._save(force=True)
