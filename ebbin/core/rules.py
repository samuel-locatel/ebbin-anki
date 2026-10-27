from dataclasses import dataclass, field

BASE_XP = {1: 2, 2: 6, 3: 10, 4: 10}
SIDE_MISSION_BONUS = 30
STREAK_DAY_BONUS = 20

RANKS: list[tuple[int, str]] = [
    (1, "Rabisco"), (5, "Rascunho"), (10, "Esboço"), (15, "Anotação"),
    (20, "Caderno"), (25, "Fichário"), (30, "Apostila"), (35, "Compêndio"),
    (40, "Tratado"), (45, "Enciclopédia"), (50, "Biblioteca"), (60, "Ebbinghaus"),
]


def _round_half_up(x: float) -> int:
    return int(x + 0.5)


@dataclass(frozen=True)
class Combo:
    count: int = 0

    def to_dict(self) -> dict:
        return {"count": self.count}

    @classmethod
    def from_dict(cls, d: dict) -> "Combo":
        return cls(int(d.get("count", 0)))


def next_combo(c: Combo, ease: int) -> Combo:
    if ease == 1:
        return Combo(0)
    if ease == 2:
        return c
    return Combo(c.count + 1)


def combo_multiplier(c: Combo) -> float:
    return min(1.5, 1 + 0.05 * c.count)


def answer_xp(ease: int, combo_after: Combo, diminished: bool) -> int:
    return _round_half_up(
        BASE_XP[ease] * combo_multiplier(combo_after) * (0.5 if diminished else 1)
    )


def xp_for_level(level: int) -> int:
    return _round_half_up(400 * 1.06 ** (level - 1))


@dataclass(frozen=True)
class LevelInfo:
    level: int
    into: int
    needed: int


def level_from_total(total_xp: int) -> LevelInfo:
    level, remaining = 1, max(0, total_xp)
    while remaining >= xp_for_level(level):
        remaining -= xp_for_level(level)
        level += 1
    return LevelInfo(level, remaining, xp_for_level(level))


def rank_for(level: int) -> str:
    name = RANKS[0][1]
    for threshold, rank in RANKS:
        if threshold <= level:
            name = rank
    return name


def main_mission_bonus(level: int) -> int:
    return 80 + 5 * level


@dataclass
class XpLedger:
    answers: dict[int, int] = field(default_factory=dict)
    bonuses: dict[str, int] = field(default_factory=dict)

    def total(self, bootstrap: int) -> int:
        return bootstrap + sum(self.answers.values()) + sum(self.bonuses.values())

    def reconcile(self, existing_revlog_ids: set[int]) -> list[int]:
        removed = [i for i in self.answers if i not in existing_revlog_ids]
        for i in removed:
            del self.answers[i]
        return removed

    def to_dict(self) -> dict:
        return {"answers": dict(self.answers), "bonuses": dict(self.bonuses)}

    @classmethod
    def from_dict(cls, d: dict) -> "XpLedger":
        return cls(
            {int(k): int(v) for k, v in d.get("answers", {}).items()},
            {str(k): int(v) for k, v in d.get("bonuses", {}).items()},
        )
