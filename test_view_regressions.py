from PySide6.QtCore import QRectF

try:
    from .model import Overflow, TextObject, VAlign, Paragraph
    from .view import TextObjectView
except ImportError:  # pragma: no cover - support direct test execution
    from model import Overflow, TextObject, VAlign, Paragraph
    from view import TextObjectView


def test_vertical_offset_respects_autofit_shrink():
    obj = TextObject(QRectF(0, 0, 200, 200), paragraphs=[Paragraph("hello")])
    obj.valign = VAlign.MIDDLE
    obj.overflow = Overflow.AUTOFIT_SHRINK

    view = TextObjectView(obj)
    assert view._vertical_offset(view._layout_result, obj.content_rect()) == 0.0


def test_package_exports_public_api():
    import __init__ as pkg

    assert hasattr(pkg, "TextObjectView")
    assert "TextObjectView" in getattr(pkg, "__all__", [])
