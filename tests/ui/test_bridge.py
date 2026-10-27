import pytest

from ebbin.ui import bridge, state


class FakeEngine:
    def __init__(self):
        self.calls = []

    def pomo_start(self):
        self.calls.append("start")
        return {"phase": "focus"}

    def pomo_pause(self):
        return {"phase": "paused"}

    def pomo_resume(self):
        return {"phase": "focus"}

    def pomo_stop(self):
        return {"phase": "idle"}


@pytest.fixture(autouse=True)
def _reset():
    saved = dict(bridge._handlers)
    yield
    bridge._handlers.clear()
    bridge._handlers.update(saved)
    state.set_engine(None)


def test_parse():
    assert bridge.parse("ebbin:pomo_start") == ("pomo_start", None)
    assert bridge.parse("ebbin:dismiss:{\"id\": \"fsrs\"}") == ("dismiss", {"id": "fsrs"})
    assert bridge.parse("ebbin:open_window:metrics") == ("open_window", "metrics")
    assert bridge.parse("ans") is None
    assert bridge.parse("ebbin:") is None
    assert bridge.parse(123) is None


def test_passthrough_for_foreign_messages():
    assert bridge.handle((False, None), "ease3", None) == (False, None)
    assert bridge.handle((True, "x"), "ease3", None) == (True, "x")


def test_pomo_commands_call_engine():
    eng = FakeEngine()
    state.set_engine(eng)
    assert bridge.handle((False, None), "ebbin:pomo_start", None) == (True, {"phase": "focus"})
    assert eng.calls == ["start"]
    assert bridge.handle((False, None), "ebbin:pomo_stop:null", None) == (True, {"phase": "idle"})


def test_pomo_without_engine_is_none():
    assert bridge.handle((False, None), "ebbin:pomo_start", None) == (True, None)


def test_register_custom_and_unknown_and_error(capsys):
    bridge.register("hello", lambda arg: {"got": arg})
    assert bridge.handle((False, None), 'ebbin:hello:[1,2]', None) == (True, {"got": [1, 2]})
    assert bridge.handle((False, None), "ebbin:nope", None) == (True, None)
    assert "unknown bridge command" in capsys.readouterr().out

    def boom(_):
        raise RuntimeError("x")
    bridge.register("boom", boom)
    assert bridge.handle((False, None), "ebbin:boom", None) == (True, None)
    assert "[ebbin] bridge command boom failed" in capsys.readouterr().out


def test_stubs_return_none():
    assert bridge.handle((False, None), "ebbin:open_window:metrics", None) == (True, None)
    assert bridge.handle((False, None), "ebbin:dismiss:\"fsrs\"", None) == (True, None)
