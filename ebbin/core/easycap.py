"""Easy-interval cap: JS block for Anki's custom scheduling (cardStateCustomizer)."""

START = "// ebbin:start"
END = "// ebbin:end"

_TEMPLATE = """// ebbin:start
(function () {
  const RATIO = __RATIO__, FIRST_MAX = __FIRST__;
  function rev(s) { return s && s.normal ? s.normal.review : (s && s.filtered && s.filtered.rescheduling ? s.filtered.rescheduling.originalState.review : null); }
  const g = rev(states.good), e = rev(states.easy);
  if (!e) return;
  if (g) { e.scheduledDays = Math.min(e.scheduledDays, Math.max(g.scheduledDays + 1, Math.round(g.scheduledDays * RATIO))); }
  else   { e.scheduledDays = Math.min(e.scheduledDays, FIRST_MAX); }
})();
// ebbin:end"""


def block(ratio: float, first_max_days: int) -> str:
    return _TEMPLATE.replace("__RATIO__", repr(float(ratio))).replace("__FIRST__", str(int(first_max_days)))


def balanced(existing: str) -> bool:
    """True when the text has no Ebbin markers or exactly one START followed by one END."""
    ns, ne = existing.count(START), existing.count(END)
    if ns == 0 and ne == 0:
        return True
    return ns == 1 and ne == 1 and existing.find(START) < existing.find(END)


def _span(existing: str) -> tuple[int, int] | None:
    i = existing.find(START)
    if i < 0:
        return None
    j = existing.find(END, i)
    if j < 0:
        return None
    return i, j + len(END)


def install(existing: str, block: str) -> str:
    if not balanced(existing):  # never touch text with corrupted markers
        return existing
    span = _span(existing)
    if span:
        return existing[: span[0]] + block + existing[span[1]:]
    if not existing.strip():
        return block
    return existing + "\n" + block


def remove(existing: str) -> str:
    if not balanced(existing):
        return existing
    span = _span(existing)
    if not span:
        return existing
    i, j = span
    if i > 0 and existing[i - 1] == "\n":
        i -= 1
    return existing[:i] + existing[j:]
