from dataclasses import dataclass


@dataclass(frozen=True)
class Answer:
    revlog_id: int
    cid: int
    did: int
    ease: int
    time_ms: int
    day: int
    at_ms: int


@dataclass(frozen=True)
class ReviewRow:
    id: int
    cid: int
    did: int
    deck: str
    notetype: str
    tags: str
    ease: int
    time_ms: int
    type: int
    day: int
    hour: int
    n_items: int


@dataclass(frozen=True)
class CardSnap:
    stability: float | None
    retrievability: float | None
    ctype: int
