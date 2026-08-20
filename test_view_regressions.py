import importlib
import os
import sys
from pathlib import Path

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

try:
    from .model import (Overflow, SizingMode, TextObject, VAlign, Paragraph,
                        CharFormat)
    from .view import TextObjectView
    from .layout_engine import LayoutEngine
    from .cursor import TextCursor, Position
except ImportError:  # pragma: no cover - support direct test execution
    from model import (Overflow, SizingMode, TextObject, VAlign, Paragraph,
                       CharFormat)
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
    assert hasattr(pkg, "TextBox")
    assert "TextBox" in getattr(pkg, "__all__", [])


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


def test_selection_paints_without_qt_cursor_coordinate_errors():
    obj = TextObject(QRectF(0, 0, 240, 120), paragraphs=[Paragraph("selection render")])
    view = TextObjectView(obj)
    view.cursor.set_selection(Position(0, 0), Position(0, 9))
    image = QImage(240, 120, QImage.Format_ARGB32)
    image.fill(0)

    view.render(image)

    assert not image.isNull()


def test_textbox_sizing_modes_and_placeholder():
    try:
        from .textbox import TextBox
    except ImportError:
        from textbox import TextBox

    auto = TextBox(text="texte initial", width=420, height=220)
    assert auto.model.sizing_mode == SizingMode.AUTO_FIT_CONTENT
    assert auto.width() < 420

    placeholder = TextBox(placeholder="Votre titre", width=420, height=220)
    assert placeholder.width() >= 40
    assert placeholder.model.placeholder == "Votre titre"

    free = TextBox(text="free", sizing="free_resize", width=200, height=100)
    free.resize_box(300, 140)
    assert free.width() == 300

    locked = TextBox(text="locked", sizing="locked", width=200, height=100)
    locked.resize_box(300, 140)
    assert locked.width() == 200


def test_arrow_keys_collapse_selection_to_the_expected_edge():
    view = TextObjectView(TextObject(QRectF(0, 0, 200, 100),
                                     [Paragraph("abcdef")]))
    cursor = view.cursor
    cursor.set_selection(Position(0, 1), Position(0, 5))

    view._move(-1, extend=False)
    assert cursor.position == Position(0, 1)
    assert not cursor.has_selection()

    cursor.set_selection(Position(0, 1), Position(0, 5))
    view._move(1, extend=False)
    assert cursor.position == Position(0, 5)
    assert not cursor.has_selection()


def test_multiline_insert_creates_paragraphs():
    obj = TextObject(QRectF(0, 0, 200, 100), [Paragraph("beforeafter")])
    cursor = TextCursor(obj)
    cursor.position = Position(0, 6)

    cursor.insert_text("one\ntwo")

    assert [paragraph.text for paragraph in obj.paragraphs] == [
        "beforeone", "twoafter"
    ]
    assert cursor.position == Position(1, 3)


def test_format_read_is_not_an_undo_edit():
    obj = TextObject(QRectF(0, 0, 200, 100), [Paragraph("hello")])
    cursor = TextCursor(obj)
    cursor.set_selection(Position(0, 0), Position(0, 5))
    cursor.current_format()
    cursor.apply_format_to_selection_or_pending(bold=True)

    assert obj.paragraphs[0].format_at(0).bold
    assert cursor.undo()
    assert not obj.paragraphs[0].format_at(0).bold


def test_auto_fit_uses_character_format_metrics():
    try:
        from .textbox import TextBox
    except ImportError:
        from textbox import TextBox
    large = Paragraph("Large", default_format=CharFormat(font_size=48.0))
    box = TextBox(paragraphs=[large], width=100, height=40)

    assert box.height() >= 50
    assert box.width() > 100


def test_physical_units_are_converted_with_explicit_dpi():
    try:
        from .textbox import TextBox
        from .units import Unit, from_pixels, to_pixels
    except ImportError:
        from textbox import TextBox
        from units import Unit, from_pixels, to_pixels

    assert abs(to_pixels(25.4, Unit.MILLIMETER, 300) - 300.0) < 0.001
    assert abs(from_pixels(300, Unit.MILLIMETER, 300) - 25.4) < 0.001
    box = TextBox(text="Prix", x=10, y=5, width=50, height=20,
                  unit="mm", dpi=300, sizing="free_resize")
    assert abs(box.width() - to_pixels(50, "mm", 300)) <= 1
    assert abs(box.x() - to_pixels(10, "mm", 300)) <= 1


def test_label_field_subclasses_keep_textbox_behavior_and_domain_defaults():
    try:
        from .label_fields import BRAND, DESCRIPTION, PARTNO, PRICE
    except ImportError:
        from label_fields import BRAND, DESCRIPTION, PARTNO, PRICE

    brand = BRAND("Acme")
    price = PRICE("12,995", currency="EUR", decimals=2)
    description = DESCRIPTION("Produit")
    part_number = PARTNO("AC-2048")

    assert brand.text == "Acme"
    assert price.text == "13,00 EUR"
    assert price.field_id == "price"
    assert description.obj.sizing_mode == SizingMode.FREE_RESIZE
    assert part_number.text == "AC-2048"
    assert len(price._handle_rects()) == 9
