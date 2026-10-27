import pytest

from ebbin.ui.skinmap import PAGES, assets_for, context_name

_EMPTY = {"css": [], "js": [], "body_class": ""}


@pytest.mark.parametrize("name, page", [
    ("aqt.reviewer.Reviewer", "ebbin-reviewer"),
    ("aqt.reviewer.ReviewerBottomBar", "ebbin-bottom"),
    ("aqt.deckbrowser.DeckBrowser", "ebbin-decks"),
    ("aqt.deckbrowser.DeckBrowserBottomBar", "ebbin-bottom"),
    ("aqt.overview.Overview", "ebbin-overview"),
    ("aqt.overview.OverviewBottomBar", "ebbin-bottom"),
    ("aqt.toolbar.TopToolbar", "ebbin-toolbar"),
])
def test_skinned_contexts(name, page):
    a = assets_for(name, True)
    assert a["css"] == ["theme.css", "skin.css"]  # skin.css always after theme.css
    assert a["js"] == ["sketch.js", "skin.js"]
    assert a["body_class"] == f"ebbin-skin {page}"


def test_every_page_is_mapped():
    assert len(PAGES) == 7


@pytest.mark.parametrize("name", [
    "aqt.reviewer.Reviewer", "aqt.deckbrowser.DeckBrowser", "aqt.toolbar.TopToolbar",
])
def test_skin_off_injects_nothing(name):
    assert assets_for(name, False) == _EMPTY


@pytest.mark.parametrize("name", [
    "aqt.toolbar.BottomToolbar", "aqt.editor.Editor", "ebbin.ui.popup.PopupDialog", "Reviewer", "",
])
def test_unknown_contexts_untouched(name):
    assert assets_for(name, True) == _EMPTY


def test_context_name_is_module_qualified():
    class Reviewer:  # same short name as Anki's, different module
        pass
    assert context_name(Reviewer()) == f"{__name__}.test_context_name_is_module_qualified.<locals>.Reviewer"
    assert assets_for(context_name(Reviewer()), True) == _EMPTY
    assert context_name(None) == "builtins.NoneType"
