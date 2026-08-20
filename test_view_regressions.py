import importlib
import os
import sys
from pathlib import Path

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtWidgets import QApplication

try:
    from .model import Overflow, TextObject, VAlign, Paragraph, CharFormat
    from .view import TextObjectView
    from .layout_engine import LayoutEngine
    from .cursor import TextCursor, Position
except ImportError:  # pragma: no cover - support direct test execution
    from model import Overflow, TextObject, VAlign, Paragraph, CharFormat
    from view import TextObjectView
    from layout_engine import LayoutEngine
    from cursor import TextCursor, Position


app = QApplication.instance() or QApplication([])


def test_vertical_offset_respects_autofit_shrink():
    obj = TextObject(QRectF(0, 0, 200, 200), paragraphs=[Paragraph("hello")])
    obj.valign = VAlign.MIDDLE
    obj.overflow = Overflow.AUTOFIT_SHRINK

    view = TextObjectView(obj)
    assert view._vertical_offset(view._layout_result, obj.content_rect()) == 0.0


def test_package_exports_public_api():
    package_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(package_root.parent))
    pkg = importlib.import_module(package_root.name)

    assert hasattr(pkg, "TextObjectView")
    assert "TextObjectView" in getattr(pkg, "__all__", [])


def test_bounding_box_has_eight_handles_and_respects_minimum_size():
    obj = TextObject(QRectF(0, 0, 200, 100), paragraphs=[Paragraph("hello")])
    view = TextObjectView(obj)

    handles = set(view._handle_rects())
    assert handles - {"rotate"} == {
        "top_left", "top", "top_right", "right",
        "bottom_right", "bottom", "bottom_left", "left",
    }
    assert "rotate" in handles

    view._drag_geometry = view.geometry()
    view._drag_handle = "top_left"
    view._resize_geometry(QPointF(500, 500), Qt.NoModifier)

    assert view.width() >= view.MIN_WIDTH
    assert view.height() >= view.MIN_HEIGHT


def test_rotation_handle_and_inverse_transform_are_available():
    obj = TextObject(QRectF(0, 0, 200, 100), paragraphs=[Paragraph("hello")])
    view = TextObjectView(obj)
    view.obj.rotation = 45.0

    assert view._handle_at(view._handle_rects()["rotate"].center()) == "rotate"
    local = QPointF(30, 20)
    transformed = view._view_point(local)
    restored = view._local_point(transformed)
    assert abs(restored.x() - local.x()) < 0.001
    assert abs(restored.y() - local.y()) < 0.001


def test_autofit_grow_expands_the_model_box():
    obj = TextObject(QRectF(0, 0, 100, 20), paragraphs=[Paragraph("long text " * 20)])
    obj.overflow = Overflow.AUTOFIT_GROW
    result = LayoutEngine().layout(obj)

    assert result.total_height > 0
    assert obj.box.height() >= result.total_height + obj.margins[2] + obj.margins[3]


def test_cursor_preserves_character_format_and_supports_undo_redo():
    paragraph = Paragraph("bold", default_format=CharFormat(bold=True))
    cursor = TextCursor(TextObject(QRectF(0, 0, 200, 100), [paragraph]))
    cursor.position = Position(0, 4)
    cursor.insert_paragraph_break()
    cursor.insert_text("x")

    assert cursor.obj.paragraphs[1].format_at(0).bold
    assert cursor.undo()
    assert cursor.obj.paragraphs[1].text == ""
    assert cursor.redo()
    assert cursor.obj.paragraphs[1].text == "x"
