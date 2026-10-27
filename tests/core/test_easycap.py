from ebbin.core import easycap
from ebbin.ui import schedtools

USER = "// mine\nfoo();"
KEY = "CARD_STATE_CUSTOMIZER"


def test_install_into_empty_then_remove():
    b = easycap.block(1.5, 4)
    out = easycap.install("", b)
    assert out == b
    assert easycap.remove(out) == ""


def test_block_markers_and_values():
    b = easycap.block(1.5, 4)
    assert b.startswith(easycap.START) and b.endswith(easycap.END)
    assert "RATIO = 1.5, FIRST_MAX = 4;" in b


def test_install_twice_single_block_and_remove_roundtrip():
    b = easycap.block(1.5, 4)
    once = easycap.install(USER, b)
    twice = easycap.install(once, b)
    assert once == twice
    assert twice.count(easycap.START) == 1
    assert easycap.remove(twice) == USER


def test_remove_keeps_trailing_newline_user_code():
    user = "foo();\n"
    out = easycap.install(user, easycap.block(1.5, 4))
    assert easycap.remove(out) == user


def test_remove_noop_without_block():
    assert easycap.remove(USER) == USER


def test_changing_ratio_replaces_in_place():
    once = easycap.install(USER, easycap.block(1.5, 4))
    new = easycap.install(once, easycap.block(2.0, 7))
    assert "RATIO = 2.0, FIRST_MAX = 7;" in new
    assert "RATIO = 1.5" not in new
    assert new.count(easycap.START) == 1
    assert easycap.remove(new) == USER


def test_apply_easy_cap_enable_disable(col):
    col.set_config_string(KEY, USER)
    cfg = {"easy_cap": {"enabled": True, "ratio": 1.5, "first_max_days": 4}}
    schedtools.apply_easy_cap(col, cfg)
    assert easycap.START in col.get_config_string(KEY)
    schedtools.apply_easy_cap(col, cfg)
    assert col.get_config_string(KEY).count(easycap.START) == 1
    cfg["easy_cap"]["enabled"] = False
    schedtools.apply_easy_cap(col, cfg)
    assert col.get_config_string(KEY) == USER


def test_apply_easy_cap_missing_key(col):
    cfg = {"easy_cap": {"enabled": True, "ratio": 1.5, "first_max_days": 4}}
    schedtools.apply_easy_cap(col, cfg)
    assert easycap.START in col.get_config_string(KEY)


B = easycap.block(1.5, 4)
UNBALANCED = {
    "start_without_end": "foo();\n// ebbin:start\nbar();",
    "end_without_start": "foo();\n// ebbin:end\nbar();",
    "two_starts": "// ebbin:start\na();\n// ebbin:start\nb();\n// ebbin:end",
    "end_before_start": "// ebbin:end\nx();\n// ebbin:start",
}


def test_unbalanced_markers_left_untouched_by_install_and_remove():
    for name, text in UNBALANCED.items():
        assert easycap.install(text, B) == text, name
        assert easycap.remove(text) == text, name


def test_apply_easy_cap_skips_and_logs_on_corrupted_markers(col, capsys):
    bad = UNBALANCED["start_without_end"]
    col.set_config_string(KEY, bad)
    for enabled in (True, False):
        cfg = {"easy_cap": {"enabled": enabled, "ratio": 1.5, "first_max_days": 4}}
        schedtools.apply_easy_cap(col, cfg)
        assert col.get_config_string(KEY) == bad
    assert "[ebbin] marcadores do Ebbin corrompidos no Agendamento personalizado; não alterado" \
        in capsys.readouterr().out
