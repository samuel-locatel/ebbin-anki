"""Settings validation and window helpers (no aqt imports)."""
from __future__ import annotations

import json
from copy import deepcopy

_INT_RANGES = {
    ("pomodoro", "focus"): (1, 180, "Foco"),
    ("pomodoro", "short"): (1, 60, "Pausa curta"),
    ("pomodoro", "long"): (1, 120, "Pausa longa"),
    ("pomodoro", "cycles"): (1, 12, "Ciclos"),
    ("pomodoro", "idle_pause_s"): (10, 3600, "Pausa por inatividade"),
    ("easy_cap", "first_max_days"): (1, 30, "Máx. dias do primeiro intervalo"),
}
_FLOAT_RANGES = {
    ("easy_cap", "ratio"): (1.2, 3.0, "Razão do Fácil"),
    ("sounds", "volume"): (0.0, 1.0, "Volume"),
    ("rescued_r", None): (0.5, 0.99, "Retrievability de resgate"),
}
_BOOLS = (("pomodoro", "autostart"), ("easy_cap", "enabled"), ("sounds", "enabled"),
          ("import", "move_after"), ("auto_new_per_day", None), ("skin", None))
_THEMES = ("night", "slate")
_DUPES = ("preserve", "update")


def _get(d: dict, path: tuple):
    k, sub = path
    return d[k] if sub is None else d[k][sub]


def _set(d: dict, path: tuple, v) -> None:
    k, sub = path
    if sub is None:
        d[k] = v
    else:
        d[k][sub] = v


def _num(v, label: str):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{label}: valor inválido")
    return v


def validate_config(incoming: dict, base: dict) -> dict:
    """Returns a new full config (base overlaid with `incoming`) or raises ValueError(pt-BR)."""
    if not isinstance(incoming, dict):
        raise ValueError("configuração inválida")
    cfg = deepcopy(base)
    for key in base:
        if key not in incoming:
            continue
        if isinstance(base[key], dict):
            if not isinstance(incoming[key], dict):
                raise ValueError("configuração inválida")
            for sub in base[key]:
                if sub in incoming[key]:
                    cfg[key][sub] = incoming[key][sub]
        else:
            cfg[key] = incoming[key]

    for path, (lo, hi, label) in _INT_RANGES.items():
        v = _num(_get(cfg, path), label)
        if v != int(v) or not lo <= v <= hi:
            raise ValueError(f"{label}: use um número inteiro entre {lo} e {hi}")
        _set(cfg, path, int(v))
    v = _num(cfg["budget_min"], "Orçamento diário")
    if not 1 <= v <= 600:
        raise ValueError("Orçamento diário: use um valor entre 1 e 600 min")
    cfg["budget_min"] = v
    v = _num(cfg["mastered_days"], "Dominado (dias)")
    if not 1 <= v <= 3650:
        raise ValueError("Dominado (dias): use um valor entre 1 e 3650")
    cfg["mastered_days"] = v
    for path, (lo, hi, label) in _FLOAT_RANGES.items():
        v = float(_num(_get(cfg, path), label))
        if not lo <= v <= hi:
            raise ValueError(f"{label}: use um valor entre {lo:g} e {hi:g}".replace(".", ","))
        _set(cfg, path, v)
    for path in _BOOLS:
        if not isinstance(_get(cfg, path), bool):
            raise ValueError("configuração inválida")
    if cfg["dark_theme"] not in _THEMES:
        raise ValueError("Tema escuro inválido")
    if cfg["import"]["dupe"] not in _DUPES:
        raise ValueError("Duplicados: valor inválido")
    dest = cfg["import"]["dest"]
    if not isinstance(dest, str) or not dest.strip():
        raise ValueError("Pasta de destino: obrigatória")
    cfg["import"]["dest"] = dest.strip()
    return cfg


def sanitize_config(cfg, defaults: dict) -> tuple[dict, list[str]]:
    """Valid full config from a possibly hand-edited one: invalid keys fall back to `defaults`.

    Returns (config, dotted paths that were replaced)."""
    if not isinstance(cfg, dict):
        return deepcopy(defaults), ["*"]
    try:
        return validate_config(cfg, defaults), []
    except ValueError:
        pass
    out, bad = {}, []
    for key, dv in defaults.items():
        if key not in cfg:
            continue
        if isinstance(dv, dict):
            if not isinstance(cfg[key], dict):
                bad.append(key)
                continue
            sub = {}
            for k in dv:
                if k not in cfg[key]:
                    continue
                try:
                    validate_config({key: {k: cfg[key][k]}}, defaults)
                    sub[k] = cfg[key][k]
                except ValueError:
                    bad.append(f"{key}.{k}")
            if sub:
                out[key] = sub
        else:
            try:
                validate_config({key: cfg[key]}, defaults)
                out[key] = cfg[key]
            except ValueError:
                bad.append(key)
    try:
        return validate_config(out, defaults), bad
    except ValueError:  # cross-key problem we could not isolate
        return deepcopy(defaults), ["*"]


def webview_config(cfg: dict) -> dict:
    """What the reviewer/popup/strip scripts need after a settings change."""
    return {"sounds_enabled": cfg["sounds"]["enabled"], "volume": cfg["sounds"]["volume"],
            "dark_theme": cfg["dark_theme"]}


def export_json(state_path) -> str:
    """Pretty JSON of the persisted state file (raw copy)."""
    with open(state_path, encoding="utf-8") as f:
        return json.dumps(json.load(f), ensure_ascii=False, indent=2)
