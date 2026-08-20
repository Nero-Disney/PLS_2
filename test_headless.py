"""Smoke tests for the production view in a headless Qt environment."""

import os

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication

try:
    from .model import Paragraph, TextObject
    from .view import TextObjectView
except ImportError:  # pragma: no cover - support direct test execution
    from model import Paragraph, TextObject
    from view import TextObjectView


app = QApplication.instance() or QApplication([])


def test_production_view_constructs_headless():
    view = TextObjectView(TextObject(QRectF(0, 0, 240, 120),
                                     [Paragraph("headless")]))
    assert view.obj.plain_text() == "headless"
    assert "rotate" in view._handle_rects()


def test_final_app_is_only_a_bootstrap_layer():
    try:
        from .final_app import create_demo_object
    except ImportError:
        from final_app import create_demo_object

    obj = create_demo_object()
    assert obj.plain_text() == "Bonjour PLS_2 !"
    assert obj.__class__.__module__.endswith("model")
