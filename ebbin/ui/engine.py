"""Live engine: turns each review answer into XP, combo, missions, streak, sessions
and pomodoro state. No aqt imports (testable against a plain Collection)."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from pathlib import Path

from ebbin.core import pomodoro
from ebbin.core.challenge import (
    DayMissions, adapt, capacity, comeback_m, evaluate, main_text, make_main, make_sides,
)
from ebbin.core.mastery import became_mastered, is_rescued
from ebbin.core.metrics import project_load
from ebbin.core.objectives import Objective, countdown_text
from ebbin.core.rules import (
    SIDE_MISSION_BONUS, STREAK_DAY_BONUS, Combo, answer_xp, level_from_total,
    main_mission_bonus, next_combo, rank_for,
)
from ebbin.core.session import (
    Records, SessionRecord, SessionTracker, badge_for, is_diminished, should_popup,
    update_records,
)
from ebbin.core.streak import compute
from ebbin.data import queries as q
from ebbin.data import store
from ebbin.data.bootstrap import initial_xp

_DAY_MS = 86_400_000
_WEEK_LABELS = "stqqssd"  # Monday..Sunday (segunda..domingo)
_BADGE_PRIORITY = ("Preciso", "Relâmpago", "Resgatador", "Persistente")


@dataclass
class AnswerEvent:
    xp: int
    combo: int
    sounds: list[str]
    level_up: bool
    level: int
    mission_done: list[str]
    mastered: bool
    rescued: bool
    diminished: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _level_dict(total: int) -> dict:
    li = level_from_total(total)
    return {"level": li.level, "into": li.into, "needed": li.needed}


def history_days(col, installed_day: int) -> set[int]:
    """Pre-install history qualifies any day with a review (spec 5, first install)."""
    cutoff = q.day_start_ms(col) - (q.today(col) - installed_day) * _DAY_MS
    ids = col.db.list("select id from revlog where id < ? and type != 4 and ease != 0", cutoff)
    return {q.day_of_ms(col, i) for i in ids}


def streak_for(col, state, history: set[int] | None = None):
    """Pure-ish streak computation shared by the engine and the metrics window.
    Returns (StreakResult, qualified day set)."""
    if history is None:
        history = history_days(col, state.installed_day)
    days = set(history) | {d for d, ds in state.day_stats.items() if ds.get("qualified")}
    return compute(days, q.today(col)), days


def _bonus_day(key: str) -> int | None:
    parts = key.split(":")
    return int(parts[1]) if len(parts) >= 2 and parts[1].lstrip("-").isdigit() else None


class Engine:
    def __init__(self, col, cfg: dict, state_path: Path, clock=time.time):
        self.col = col
        self.cfg = cfg
        self.path = Path(state_path)
        self.clock = clock
        self.state = store.load(self.path)
        self.tracker = SessionTracker()
        self.pomo = pomodoro.Pomo()
        self._snaps: dict = {}
        # Current-session bookkeeping (in memory): tracker.on_answer args per answer,
        # and bonus keys earned during the session.
        self._sess_answers: list[tuple] = []
        self._sess_bonuses: dict[str, int] = {}
        self._history_days: set[int] | None = None
        if not self.path.exists():  # fresh install (store.load also renames corrupt files away)
            self.state.bootstrap_xp = initial_xp(col)
            self.state.installed_day = q.today(col)
            self.save()
        elif self.state.installed_day < 0:  # state file written before installed_day existed
            self.state.installed_day = min(self.state.missions_by_day, default=q.today(col))
            self.save()

    # ---- helpers -------------------------------------------------------------------

    def save(self) -> None:
        store.save(self.state, self.path)

    def _total(self) -> int:
        return self.state.ledger.total(self.state.bootstrap_xp)

    def _budget(self) -> float:
        return self.cfg["budget_min"]

    def _avg_s(self) -> float:
        # avg_time_s is 0.0 when every recent row has time 0; fall back to the 30 s default.
        return q.avg_time_s(self.col) or 30.0

    def _ds(self, day: int) -> dict:
        ds = self.state.day_stats.setdefault(day, {})
        ds.setdefault("max_combo", 0)
        ds.setdefault("pomodoros", 0)
        ds.setdefault("qualified", False)
        return ds

    def _rows_today(self):
        return q.reviews_since(self.col, q.day_start_ms(self.col))

    def _date_of(self, day: int) -> date:
        start = q.day_start_ms(self.col) - (q.today(self.col) - day) * _DAY_MS
        return datetime.fromtimestamp(start / 1000).date()

    def _add_bonus(self, key: str, value: int) -> bool:
        if key in self.state.ledger.bonuses:
            return False
        self.state.ledger.bonuses[key] = value
        self._sess_bonuses[key] = value
        return True

    def _drop_bonus(self, key: str) -> None:
        self.state.ledger.bonuses.pop(key, None)
        self._sess_bonuses.pop(key, None)

    def _weak_decks(self) -> list[str]:
        rows = q.reviews_since(self.col, q.day_start_ms(self.col) - 29 * _DAY_MS)
        groups: dict[str, list[int]] = {}
        for r in rows:
            groups.setdefault(r.deck, []).append(1 if r.ease > 1 else 0)
        ranked = sorted((sum(v) / len(v), deck) for deck, v in groups.items() if len(v) >= 20)
        return [deck for _, deck in ranked[:2]]

    def _missed_days(self, t: int) -> int | None:
        """Days strictly between the last review day before today and today."""
        last = self.col.db.scalar(
            "select max(id) from revlog where id < ? and type != 4 and ease != 0",
            q.day_start_ms(self.col))
        return None if last is None else t - q.day_of_ms(self.col, last) - 1

    def ensure_day(self) -> None:
        st = self.state
        t = q.today(self.col)
        if st.combo_day != t:
            st.combo, st.combo_day = Combo(0), t
        if t in st.missions_by_day:
            return
        earlier = [d for d in st.missions_by_day if d < t]
        if earlier:
            prev = st.missions_by_day[max(earlier)]
            st.m, st.met_streak, st.miss_streak = adapt(
                st.m, st.met_streak, st.miss_streak, bool(prev.get("main_done")))
        missed = self._missed_days(t)
        if missed is not None and missed >= 3:  # spec 4.7: "≥ 3 dias sem revisar"
            st.comeback_days_left = 3
        if st.comeback_days_left > 0:
            m_used = comeback_m(3, 3 - st.comeback_days_left)
            st.comeback_days_left -= 1
        else:
            m_used = st.m
        cap = capacity(self._budget(), self._avg_s())
        main = make_main(cap, m_used, q.due_today(self.col), q.new_available(self.col))
        rows14 = [r for r in q.reviews_since(self.col, q.day_start_ms(self.col) - 14 * _DAY_MS)
                  if r.day < t]
        yesterday = st.missions_by_day.get(t - 1, {})
        y_types = {s["type"] for s in yesterday.get("sides", [])}
        sides = make_sides(t, rows14, y_types, self._weak_decks())
        st.missions_by_day[t] = DayMissions(t, main, sides, m_used=m_used).to_dict()
        self.save()

    def _refresh_missions(self, t: int, rows_today, due: int, rid: int | None) -> list[str]:
        """Re-evaluate today's missions, award new bonuses; returns newly done names.

        Each completion (main, each side type, the day's qualification) is attributed in
        day_stats[t]["done_by"] to the revlog id `rid` that caused it (None when caused by
        a pomodoro), so on_undo revokes only completions whose answer was undone."""
        dm = DayMissions.from_dict(self.state.missions_by_day[t])
        ds = self._ds(t)
        done_by = ds.setdefault("done_by", {})
        new = evaluate(dm, rows_today, due, ds["max_combo"], ds["pomodoros"])
        done: list[str] = []
        if new.main_done and not dm.main_done:
            done_by["main"] = rid
            if self._add_bonus(f"main:{t}", main_mission_bonus(level_from_total(self._total()).level)):
                done.append("main")
        for s in new.sides_done:
            if s not in dm.sides_done:
                done_by[s] = rid
                if self._add_bonus(f"side:{t}:{s}", SIDE_MISSION_BONUS):
                    done.append(s)
        self.state.missions_by_day[t] = new.to_dict()
        if new.main_done or due == 0:
            if not ds["qualified"]:
                ds["qualified"] = True
                done_by["qualified"] = rid
            if due == 0:
                ds["due_zero"] = True
            self._add_bonus(f"streak:{t}", STREAK_DAY_BONUS)
        return done

    def _streak(self):
        if self._history_days is None:
            self._history_days = history_days(self.col, self.state.installed_day)
        return streak_for(self.col, self.state, self._history_days)

    def _main_done(self, t: int) -> bool:
        return bool(self.state.missions_by_day.get(t, {}).get("main_done"))

    # ---- reviewer flow -------------------------------------------------------------

    def before_show(self, cid: int) -> None:
        self.ensure_day()
        self._snaps[cid] = q.card_snapshot(self.col, cid)

    def on_answer(self, cid: int, ease: int) -> AnswerEvent:
        self.ensure_day()
        st, col = self.state, self.col
        t = q.today(col)
        rid, time_ms = col.db.first(
            "select id, time from revlog where cid = ? order by id desc limit 1", cid)
        level_before = level_from_total(self._total()).level
        main_done_before = self._main_done(t)

        combo = next_combo(st.combo, ease)
        st.combo, st.combo_day = combo, t
        ds = self._ds(t)
        ds["max_combo"] = max(ds["max_combo"], combo.count)

        rows_today = self._rows_today()
        review_s = sum(r.time_ms for r in rows_today) // 1000
        diminished = is_diminished(main_done_before, ds["pomodoros"] > 0, review_s, self._budget())
        xp = answer_xp(ease, combo, diminished)
        st.ledger.answers[rid] = xp

        mastered = rescued = False
        before = self._snaps.pop(cid, None)
        if before is not None:
            after = q.card_snapshot(col, cid)
            mastered = became_mastered(before.stability, after.stability,
                                       self.cfg.get("mastered_days", 21))
            rescued = is_rescued(before.retrievability, ease, self.cfg.get("rescued_r", 0.85))
        if mastered:
            st.mastered[rid] = cid
        if rescued:
            st.rescued[rid] = cid

        args = (rid, ease, xp, time_ms, rescued, mastered, combo.count)
        closed = self.tracker.on_answer(*args)
        if closed is not None:
            st.sessions.append(closed.to_dict())
        if self.tracker.current.answers == 1:  # a new session just opened
            self._sess_answers, self._sess_bonuses = [], {}
        self._sess_answers.append(args)

        mission_done = self._refresh_missions(t, rows_today, q.due_today(col), rid)

        level_after = level_from_total(self._total()).level
        level_up = level_after > level_before
        if ease == 1:
            sounds = ["again"]
        elif ease == 2:
            sounds = ["hard"]
        else:
            sounds = [f"combo:{combo.count}" if combo.count >= 2 else "good"]
        if mastered:
            sounds.append("mastered")
        if "main" in mission_done:
            sounds.append("done")
        if level_up:
            sounds.append("level")

        self.save()
        return AnswerEvent(xp, combo.count, sounds, level_up, level_after, mission_done,
                           mastered, rescued, diminished)

    def on_undo(self) -> None:
        st, col = self.state, self.col
        keys = set(st.ledger.answers) | set(st.rescued) | set(st.mastered)
        existing: set[int] = set()
        if keys:
            existing = set(col.db.list("select id from revlog where id >= ?", min(keys))) & keys
        removed = set(st.ledger.reconcile(existing))
        st.rescued = {k: v for k, v in st.rescued.items() if k in existing}
        st.mastered = {k: v for k, v in st.mastered.items() if k in existing}
        if not removed:  # undo of something else (note edit, bury...): keep combo and missions
            self.save()
            return
        # Combo = replay of today's remaining answers (what it was before the undone one).
        c = Combo()
        for r in self._rows_today():
            c = next_combo(c, r.ease)
        st.combo = c

        # Tracker: replay the current session without the undone answers.
        if any(a[0] in removed for a in self._sess_answers):
            pomo = bool(self.tracker.current and self.tracker.current.pomodoro)
            self._sess_answers = [a for a in self._sess_answers if a[0] not in removed]
            self.tracker = SessionTracker()
            for a in self._sess_answers:
                self.tracker.on_answer(*a)
            if pomo:
                self.tracker.mark_pomodoro()

        t = q.today(col)
        if t in st.missions_by_day:
            rows = self._rows_today()
            ds = self._ds(t)
            c, best = Combo(), 0
            for r in rows:
                c = next_combo(c, r.ease)
                best = max(best, c.count)
            ds["max_combo"] = min(ds["max_combo"], best)
            # Revoke only completions caused by an undone answer: transient conditions
            # (due reaching 0) cannot be re-derived later, so nothing else is re-evaluated.
            done_by = ds.setdefault("done_by", {})
            revoke = {k for k, r in done_by.items() if r is not None and r in removed}
            dm = DayMissions.from_dict(st.missions_by_day[t])
            if "main" in revoke:
                dm = replace(dm, main_done=False)
                self._drop_bonus(f"main:{t}")
            for side in [s for s in dm.sides_done if s in revoke]:
                dm = replace(dm, sides_done=[x for x in dm.sides_done if x != side])
                self._drop_bonus(f"side:{t}:{side}")
            st.missions_by_day[t] = dm.to_dict()
            if "qualified" in revoke:
                ds["qualified"] = False
                ds.pop("due_zero", None)
                self._drop_bonus(f"streak:{t}")
            for k in revoke:
                del done_by[k]
        self.save()

    # ---- views ---------------------------------------------------------------------

    def _missions_view(self, t: int, rows, due: int) -> list[dict]:
        dm = DayMissions.from_dict(self.state.missions_by_day[t])
        ds = self._ds(t)
        n = len(rows)
        main = dm.main
        if main.kind == "reviews":
            progress, target = n, main.target_reviews
        else:
            learned = len({r.cid for r in rows if r.type == 0})
            progress = (max(0, main.target_reviews - due) + min(learned, main.target_new))
            target = main.target_reviews + main.target_new
        if dm.main_done:
            progress = max(progress, target)
        out = [{"type": "main", "text": main_text(main), "progress": min(progress, target),
                "target": target, "done": dm.main_done}]
        for s in dm.sides:
            if s.type == "accuracy":
                prog = round(sum(1 for r in rows if r.ease > 1) / n * 100) if n else 0
                tgt = round(s.target * 100)
            elif s.type == "pace":
                prog = round(sum(r.time_ms for r in rows) / 1000 / n) if n else 0
                tgt = round(s.target)
            else:
                tgt = int(s.target)
                if s.type == "combo":
                    prog = ds["max_combo"]
                elif s.type == "focus":
                    prog = ds["pomodoros"]
                else:
                    prog = sum(1 for r in rows
                               if any(r.deck == d or r.deck.startswith(d + "::") for d in s.decks))
                prog = min(prog, tgt)
            out.append({"type": s.type, "text": s.text, "progress": prog, "target": tgt,
                        "done": s.type in dm.sides_done})
        return out

    def today_view(self) -> dict:
        self.ensure_day()
        st, col = self.state, self.col
        t = q.today(col)
        total = self._total()
        li = level_from_total(total)
        start = q.day_start_ms(col)
        xp_today = sum(v for k, v in st.ledger.answers.items() if k >= start)
        xp_today += sum(v for k, v in st.ledger.bonuses.items() if _bonus_day(k) == t)
        streak, qualified = self._streak()
        week = []
        for d in range(t - 6, t + 1):
            state = "done" if d in qualified else ("today" if d == t else "off")
            week.append({"label": _WEEK_LABELS[self._date_of(d).weekday()], "state": state})
        rows = self._rows_today()
        due = q.due_today(col)
        objective = None
        for o in st.objectives:
            if o.get("id") == st.active_objective and not o.get("archived"):
                objective = countdown_text(Objective.from_dict(o), self._date_of(t))
        ds = self._ds(t)
        cur = self.tracker.current
        return {
            "level": li.level, "rank": rank_for(li.level), "into": li.into, "needed": li.needed,
            "total_xp": total, "xp_today": xp_today,
            "xp_before_today": max(0, li.into - xp_today),
            "streak": {"current": streak.current, "best": streak.best, "freezes": streak.freezes},
            "week": week,
            "missions": self._missions_view(t, rows, due),
            "objective": objective,
            "pomodoro": self._pomo_dict(),
            "session_xp": cur.xp if cur else 0,
            "diminished": is_diminished(self._main_done(t), ds["pomodoros"] > 0,
                                        sum(r.time_ms for r in rows) // 1000, self._budget()),
            "hints": [],
        }

    def end_session(self, reason: str) -> dict | None:
        rec: SessionRecord | None = self.tracker.close(int(self.clock() * 1000))
        self._snaps.clear()
        if rec is None:
            return None
        st, col = self.state, self.col
        sess_answers, bonuses = self._sess_answers, self._sess_bonuses
        self._sess_answers, self._sess_bonuses = [], {}
        st.sessions.append(rec.to_dict())
        t = q.today(col)
        y, w, _ = self._date_of(t).isocalendar()
        records, broken = update_records(Records.from_dict(st.records), rec, f"{y}-W{w:02d}")
        st.records = records.to_dict()
        avg_s = self._avg_s()
        cap = capacity(self._budget(), avg_s)
        badge = badge_for(rec, q.median_time_s(col), cap)
        if badge:
            prev = st.badges_by_day.get(t)
            if prev not in _BADGE_PRIORITY or (
                    _BADGE_PRIORITY.index(badge) < _BADGE_PRIORITY.index(prev)):
                st.badges_by_day[t] = badge
        if not should_popup(rec, reason):
            self.save()
            return None
        total = self._total()
        streak, _ = self._streak()
        tomorrow_due = project_load(q.scheduled_due_by_day(col), 0)[1]
        first_s = sess_answers[0][3] / 1000 if sess_answers else 0
        payload = {
            "session_xp": rec.xp,
            "answers": rec.answers,
            "acc": round(rec.correct / rec.answers * 100) if rec.answers else 0,
            "duration_s": round((rec.end_ms - rec.start_ms) / 1000 + first_s),
            "level_before": _level_dict(total - rec.xp - sum(bonuses.values())),
            "level_after": _level_dict(total),
            "main_bonus": sum(v for k, v in bonuses.items() if k.startswith("main:")),
            "streak": streak.current,
            "streak_bonus": sum(v for k, v in bonuses.items() if k.startswith("streak:")),
            "rescued": rec.rescued,
            "mastered_new": rec.mastered,
            "badge": badge,
            "records": broken,
            "tomorrow_due": tomorrow_due,
            "fits_budget": tomorrow_due * avg_s <= self._budget() * 60,
        }
        self.save()
        return payload

    # ---- pomodoro ------------------------------------------------------------------

    def _pomo_dict(self) -> dict:
        return {"phase": self.pomo.phase, "remaining_s": self.pomo.remaining_s,
                "cycle": self.pomo.cycle}

    def pomo_start(self) -> dict:
        self.pomo = pomodoro.start(self.cfg["pomodoro"], self.pomo.cycle)
        return self._pomo_dict()

    def pomo_pause(self) -> dict:
        if self.pomo.phase in ("focus", "short", "long"):
            self.pomo = replace(self.pomo, phase="paused", paused_from=self.pomo.phase)
        return self._pomo_dict()

    def pomo_resume(self) -> dict:
        self.pomo = pomodoro.resume(self.pomo)
        return self._pomo_dict()

    def pomo_stop(self) -> dict:
        self.pomo = pomodoro.stop(self.pomo)
        return self._pomo_dict()

    def pomo_tick(self, dt_s: int, idle_s: int) -> list[str]:
        self.pomo, events = pomodoro.tick(self.pomo, dt_s, idle_s, self.cfg["pomodoro"])
        if "focus_done" in events:
            self.ensure_day()
            t = q.today(self.col)
            level_before = level_from_total(self._total()).level
            self._ds(t)["pomodoros"] += 1
            self.tracker.mark_pomodoro()
            done = self._refresh_missions(t, self._rows_today(), q.due_today(self.col), None)
            events = events + [f"mission:{d}" for d in done]
            if level_from_total(self._total()).level > level_before:
                events.append("level")
            self.save()
        return events
