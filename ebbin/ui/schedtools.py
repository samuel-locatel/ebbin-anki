"""Applies the Easy-cap block to the collection's custom scheduling JS."""
import hashlib
import json

from ebbin.core import easycap, objectives
from ebbin.data import queries as q

_KEY = "CARD_STATE_CUSTOMIZER"


def apply_easy_cap(col, cfg: dict) -> None:
    try:
        current = col.get_config_string(_KEY)
    except KeyError:
        current = ""
    if not easycap.balanced(current):
        print("[ebbin] marcadores do Ebbin corrompidos no Agendamento personalizado; não alterado")
        return
    ec = cfg["easy_cap"]
    if ec.get("enabled"):
        new = easycap.install(current, easycap.block(ec["ratio"], ec["first_max_days"]))
    else:
        new = easycap.remove(current)
    if new != current:
        col.set_config_string(_KEY, new)


_REMINDER_REVIEWS = 300
_PARAM_KEYS = ("fsrsParams6", "fsrsParams5", "fsrsWeights")


def _fsrs_params(col) -> list:
    """FSRS parameter lists of every preset (key names verified on Anki 26.08)."""
    out = []
    for conf in col.decks.all_config():
        out.append([conf.get(k) or [] for k in _PARAM_KEYS])
    return out


def fsrs_reminder_due(col, state) -> bool:
    params = _fsrs_params(col)
    count = int(col.db.scalar("select count() from revlog") or 0)
    rem = state.fsrs_reminder
    if not any(any(lst) for p in params for lst in p):  # never optimized
        return count >= _REMINDER_REVIEWS
    digest = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()
    if digest != rem.get("params_hash"):
        rem["params_hash"], rem["revlog_count"] = digest, count
        return False
    return count - int(rem.get("revlog_count", 0)) >= _REMINDER_REVIEWS


def _preset_ids(col, dids) -> dict[int, int]:
    """deck id -> preset id for normal (non-filtered) decks."""
    out = {}
    for did in dids:
        deck = col.decks.get(did)
        if not deck or deck.get("dyn"):
            continue
        out[did] = col.decks.config_dict_for_deck_id(did)["id"]
    return out


def apply_auto_new(col, state, cfg: dict, objective, capacity: int, due_today: int) -> dict | None:
    """Sets new/day on presets used only by the objective's decks. Presets shared with
    other decks are never touched (reported in skipped_shared). None when disabled/already ran."""
    if not cfg.get("auto_new_per_day") or objective is None:
        return None
    t = col.sched.today
    ds = state.day_stats.setdefault(t, {})
    if ds.get("auto_new"):
        return None
    k = objectives.suggest_new_today(capacity, due_today)
    obj_dids = q.deck_ids_under(col, objective.deck_roots)
    all_dids = {d.id for d in col.decks.all_names_and_ids()}
    mine = _preset_ids(col, obj_dids)
    others = set(_preset_ids(col, all_dids - obj_dids).values())
    applied, skipped = None, []
    for pid in sorted(set(mine.values())):
        did = next(d for d, p in mine.items() if p == pid)
        conf = col.decks.config_dict_for_deck_id(did)
        if pid in others:
            skipped.append(conf["name"])
            continue
        if conf["new"]["perDay"] != k:
            conf["new"]["perDay"] = k
            col.decks.update_config(conf)
        applied = k
    if mine:
        ds["auto_new"] = True
    return {"applied": applied, "skipped_shared": skipped}
