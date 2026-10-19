#!/usr/bin/env python3
"""Aplica as mudanças de catálogo (beni/config/migracoes.json) no config.json.

Cada migração tem um "id" único e é aplicada UMA vez por notebook; as já
aplicadas ficam em ~/.config/cozy-kids-launcher/migracoes-aplicadas.json.
O que os pais mudaram (limites, temas, PIN, tiles ocultos) não é tocado,
a não ser que a migração diga exatamente isso.

  migrar-config.py MIGRACOES.json APP_ROOT            aplica as pendentes
  migrar-config.py MIGRACOES.json APP_ROOT --marcar-todas
                                                      config novo (já veio com tudo)

Operações (campo "op"); "perfis" = "todos" (padrão) ou lista de ids de perfil:
  adicionar_tile  {tile:{id,label,emoji,cmd,visible,category}, depois_de?: id}
                  não faz nada se o perfil já tem um tile com esse id
  remover_tile    {id}
  atualizar_tile  {id, campos:{...}}           ex.: {"visible": false} ou um cmd novo
  definir         {caminho:"categoryLimits.categories.passatempo", valor, so_se_ausente?: true}
"""

import copy
import json
import os
import sys
import tempfile

HOME = os.path.expanduser("~")
CFG = os.path.join(HOME, ".config", "cozy-kids-launcher", "config.json")
APLICADAS = os.path.join(HOME, ".config", "cozy-kids-launcher", "migracoes-aplicadas.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def save_json(path, data, mode=0o600):
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=".migr.", dir=directory)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def profiles_for(cfg, which):
    profiles = cfg.get("profiles", [])
    if which in (None, "todos"):
        return profiles
    return [p for p in profiles if p.get("id") in which]


def apply_op(cfg, op):
    kind = op.get("op")
    changed = 0
    for profile in profiles_for(cfg, op.get("perfis")):
        tiles = profile.setdefault("tiles", [])
        ids = [t.get("id") for t in tiles]
        if kind == "adicionar_tile":
            tile = op["tile"]
            if tile["id"] in ids:
                continue
            after = op.get("depois_de")
            index = ids.index(after) + 1 if after in ids else len(tiles)
            tiles.insert(index, copy.deepcopy(tile))
            changed += 1
        elif kind == "remover_tile":
            if op["id"] in ids:
                profile["tiles"] = [t for t in tiles if t.get("id") != op["id"]]
                changed += 1
        elif kind == "atualizar_tile":
            for tile in tiles:
                if tile.get("id") == op["id"]:
                    tile.update(copy.deepcopy(op["campos"]))
                    changed += 1
        elif kind == "definir":
            node = profile
            *parents, last = op["caminho"].split(".")
            for key in parents:
                node = node.setdefault(key, {})
            if op.get("so_se_ausente") and last in node:
                continue
            node[last] = copy.deepcopy(op["valor"])
            changed += 1
        else:
            raise ValueError(f"operação desconhecida: {kind!r}")
    return changed


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    migrations = load_json(argv[1], {}).get("migracoes", [])
    app_root = argv[2]
    ids = [m["id"] for m in migrations]
    done = load_json(APLICADAS, {}).get("aplicadas", [])
    if "--marcar-todas" in argv:
        save_json(APLICADAS, {"aplicadas": sorted(set(done) | set(ids))})
        print(f"  {len(ids)} mudança(s) do catálogo marcadas como já aplicadas (config novo)")
        return 0
    pending = [m for m in migrations if m["id"] not in done]
    if not pending:
        print("  catálogo em dia")
        return 0
    cfg = load_json(CFG, None)
    if not isinstance(cfg, dict):
        print("  config.json não encontrado; nada a migrar")
        return 0
    new = copy.deepcopy(cfg)
    for migration in pending:
        count = sum(apply_op(new, op) for op in migration.get("operacoes", []))
        print(f"  {migration['id']}: {migration.get('descricao', '')} ({count} alteração(ões))")
    # valida com o mesmo validador do launcher antes de gravar
    sys.path.insert(0, app_root)
    from config_validation import validate_stored_config  # noqa: E402
    validate_stored_config(new, existing_pin_hash=new.get("pinHash", ""), allow_pin_hash=True)
    save_json(CFG, new)
    save_json(APLICADAS, {"aplicadas": sorted(set(done) | {m["id"] for m in pending})})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
