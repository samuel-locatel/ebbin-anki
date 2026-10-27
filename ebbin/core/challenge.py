import math
import random
import statistics
from dataclasses import asdict, dataclass, field

from ebbin.core.models import ReviewRow
from ebbin.core.rules import Combo, next_combo

MIN_ANSWERS = 15
WEAK_TARGET = 10
SIDE_TYPES = ("accuracy", "pace", "combo", "focus", "weak")


def capacity(budget_min: int, avg_s: float) -> int:
    return math.floor(budget_min * 60 / avg_s)


@dataclass
class MainMission:
    kind: str  # "reviews" | "clear_and_new"
    target_reviews: int
    target_new: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MainMission":
        return cls(str(d["kind"]), int(d["target_reviews"]), int(d.get("target_new", 0)))


def main_text(m: MainMission) -> str:
    if m.kind == "reviews":
        return f"Revisar {m.target_reviews} cards"
    if m.target_new == 0:
        return f"Zerar as revisões ({m.target_reviews})"
    return f"Zerar as revisões ({m.target_reviews}) e aprender {m.target_new} novos"


def make_main(capacity: int, m: float, due: int, new_available: int) -> MainMission:
    alvo = round(capacity * m)
    if due >= alvo:
        return MainMission("reviews", alvo, 0)
    k = min(new_available, (alvo - due) // 3)
    return MainMission("clear_and_new", due, k)


def adapt(m: float, met_streak: int, miss_streak: int, met_today: bool) -> tuple[float, int, int]:
    if met_today:
        met_streak, miss_streak = met_streak + 1, 0
    else:
        met_streak, miss_streak = 0, miss_streak + 1
    if met_streak >= 3:
        return round(min(1.3, m + 0.1), 1), 0, 0
    if miss_streak >= 2:
        return round(max(0.7, m - 0.1), 1), 0, 0
    return m, met_streak, miss_streak


def comeback_m(gap_days: int, days_into_comeback: int) -> float | None:
    if gap_days >= 3 and 0 <= days_into_comeback <= 2:
        return [0.6, 0.8, 1.0][days_into_comeback]
    return None


@dataclass
class SideMission:
    type: str
    target: float
    text: str
    decks: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"type": self.type, "target": self.target, "text": self.text,
                "decks": list(self.decks)}

    @classmethod
    def from_dict(cls, d: dict) -> "SideMission":
        return cls(str(d["type"]), float(d["target"]), str(d["text"]),
                   tuple(d.get("decks", ())))


def _leaf(name: str) -> str:
    return name.rsplit("::", 1)[-1]


def _median_daily_max_combo(rows: list[ReviewRow]) -> float:
    by_day: dict[int, list[ReviewRow]] = {}
    for r in rows:
        by_day.setdefault(r.day, []).append(r)
    maxes = []
    for day_rows in by_day.values():
        c, best = Combo(), 0
        for r in sorted(day_rows, key=lambda r: r.id):
            c = next_combo(c, r.ease)
            best = max(best, c.count)
        maxes.append(best)
    return statistics.median(maxes) if maxes else 0


def make_sides(day: int, rows14: list[ReviewRow], yesterday_types: set[str],
               weak_decks: list[str]) -> list[SideMission]:
    n = len(rows14)
    eligible = {"combo", "focus"}
    acc14 = median14 = 0.0
    if n:
        acc14 = sum(1 for r in rows14 if r.ease > 1) / n
        median14 = statistics.median(r.time_ms / 1000 for r in rows14)
    if n >= MIN_ANSWERS:
        eligible |= {"accuracy", "pace"}
    if len(weak_decks) >= 2:
        eligible.add("weak")

    rng = random.Random(day)
    pool = sorted(eligible - yesterday_types)
    if len(pool) >= 2:
        chosen = rng.sample(pool, 2)
    else:
        chosen = list(pool)
        rest = sorted(eligible & yesterday_types)
        chosen += rng.sample(rest, 2 - len(chosen))

    combo_t = int(min(15, max(5, round(_median_daily_max_combo(rows14) + 2))))
    out = []
    for t in chosen:
        if t == "accuracy":
            target = round(min(0.95, acc14 + 0.03), 2)  # the % shown is the % checked
            out.append(SideMission(t, target, f"Acerto ≥ {round(target * 100)}%"))
        elif t == "pace":
            target = int(math.floor(0.9 * median14 + 0.5))  # half-up whole seconds, shown = checked
            out.append(SideMission(t, target, f"Ritmo ≤ {round(target)}s por card"))
        elif t == "combo":
            out.append(SideMission(t, combo_t, f"{combo_t} acertos seguidos"))
        elif t == "focus":
            out.append(SideMission(t, 1, "Termine 1 pomodoro"))
        else:
            d = tuple(weak_decks[:2])
            out.append(SideMission(
                t, WEAK_TARGET, f"{WEAK_TARGET} cards de {_leaf(d[0])} e {_leaf(d[1])}", d))
    return out


@dataclass
class DayMissions:
    day: int
    main: MainMission
    sides: list[SideMission]
    main_done: bool = False
    sides_done: list[str] = field(default_factory=list)
    m_used: float = 1.0

    def to_dict(self) -> dict:
        return {"day": self.day, "main": self.main.to_dict(),
                "sides": [s.to_dict() for s in self.sides],
                "main_done": self.main_done, "sides_done": list(self.sides_done),
                "m_used": self.m_used}

    @classmethod
    def from_dict(cls, d: dict) -> "DayMissions":
        return cls(int(d["day"]), MainMission.from_dict(d["main"]),
                   [SideMission.from_dict(s) for s in d.get("sides", [])],
                   bool(d.get("main_done", False)), list(d.get("sides_done", [])),
                   float(d.get("m_used", 1.0)))


def _in_deck(deck: str, name: str) -> bool:
    return deck == name or deck.startswith(name + "::")


def evaluate(dm: DayMissions, rows_today: list[ReviewRow], due_now: int,
             max_combo_today: int, pomodoros_done_today: int) -> DayMissions:
    n = len(rows_today)
    main = dm.main
    if main.kind == "reviews":
        main_done = n >= main.target_reviews
    else:
        learned = len({r.cid for r in rows_today if r.type == 0})
        main_done = due_now == 0 and learned >= main.target_new
    main_done = main_done or dm.main_done

    done = list(dm.sides_done)
    for s in dm.sides:
        if s.type in done:
            continue
        ok = False
        if s.type == "accuracy":
            ok = n >= MIN_ANSWERS and sum(1 for r in rows_today if r.ease > 1) / n >= s.target
        elif s.type == "pace":
            ok = n >= MIN_ANSWERS and sum(r.time_ms for r in rows_today) / 1000 / n <= s.target
        elif s.type == "combo":
            ok = max_combo_today >= s.target
        elif s.type == "focus":
            ok = pomodoros_done_today >= s.target
        elif s.type == "weak":
            ok = sum(1 for r in rows_today
                     if any(_in_deck(r.deck, d) for d in s.decks)) >= s.target
        if ok:
            done.append(s.type)

    return DayMissions(dm.day, main, list(dm.sides), main_done, done, dm.m_used)
