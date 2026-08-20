"""Smoke tests for the production view in a headless Qt environment."""

import os

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication

from PLS_2.editor.model import Paragraph, TextObject
from PLS_2.editor.view import TextObjectView
from PLS_2.app.final_app import create_demo_object


app = QApplication.instance() or QApplication([])


def test_production_view_constructs_headless():
    view = TextObjectView(TextObject(QRectF(0, 0, 240, 120),
                                     [Paragraph("headless")]))
    assert view.obj.plain_text() == "headless"
    assert "rotate" in view._handle_rects()


def test_final_app_is_only_a_bootstrap_layer():
    obj = create_demo_object()
    assert obj.text == "Bonjour PLS_2 !"
    assert obj.__class__.__name__ == "TextBox"
    assert obj.model.__class__.__module__.endswith("editor.model")
