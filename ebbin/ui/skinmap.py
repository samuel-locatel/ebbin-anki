"""Which skin assets each Anki webview gets (no aqt imports)."""
from __future__ import annotations

# Anki 26.08 webview contexts (webview_will_set_content) -> page class on <body>.
PAGES = {
    "aqt.reviewer.Reviewer": "ebbin-reviewer",
    "aqt.reviewer.ReviewerBottomBar": "ebbin-bottom",
    "aqt.deckbrowser.DeckBrowser": "ebbin-decks",
    "aqt.deckbrowser.DeckBrowserBottomBar": "ebbin-bottom",
    "aqt.overview.Overview": "ebbin-overview",
    "aqt.overview.OverviewBottomBar": "ebbin-bottom",
    "aqt.toolbar.TopToolbar": "ebbin-toolbar",
}


def context_name(context) -> str:
    """Module-qualified class name, so another add-on's `Reviewer` class never matches."""
    cls = type(context)
    return f"{cls.__module__}.{cls.__qualname__}"


def assets_for(context_name: str, skin_on: bool) -> dict:
    """{"css": [...], "js": [...], "body_class": str}; file names are relative to ebbin/web."""
    page = PAGES.get(context_name)
    if not skin_on or page is None:
        return {"css": [], "js": [], "body_class": ""}
    return {"css": ["theme.css", "skin.css"], "js": ["sketch.js", "skin.js"],
            "body_class": f"ebbin-skin {page}"}
