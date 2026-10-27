import aqt

if aqt.mw is not None:
    from .ui.setup import register

    register()
