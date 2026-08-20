"""Facade publique pour creer et utiliser une textbox complete."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF
from PySide6.QtCore import QPointF

try:
    from .model import CharFormat, Paragraph, SizingMode, TextObject
    from .view import TextObjectView
    from .layout_engine import LayoutEngine
    from .units import Unit, to_pixels
except ImportError:  # pragma: no cover - support script execution
    from model import CharFormat, Paragraph, SizingMode, TextObject
    from view import TextObjectView
    from layout_engine import LayoutEngine
    from units import Unit, to_pixels


class TextBox(TextObjectView):
    """Textbox directement utilisable, avec implementation interne encapsulee.

    Les classes TextObject, TextCursor, LayoutEngine et TextObjectView restent
    disponibles pour les integrations avancees. La plupart des utilisateurs
    peuvent se limiter a cette classe.
    """

    def __init__(self, text: str = "", x: float = 0.0, y: float = 0.0,
                 width: float = 420.0, height: float = 220.0,
                 paragraphs: Optional[list[Paragraph]] = None,
                 placeholder: str = "", sizing: SizingMode | str =
                 SizingMode.AUTO_FIT_CONTENT, unit: Unit | str = Unit.PIXEL,
                 dpi: float = 96.0,
                 default_format: Optional[CharFormat] = None, parent=None):
        self.default_format = default_format or CharFormat()
        content = (paragraphs if paragraphs is not None else
                   [Paragraph(text, default_format=self.default_format)])
        self.unit = Unit(unit)
        self.dpi = dpi
        obj = TextObject(QRectF(to_pixels(x, self.unit, dpi),
                                to_pixels(y, self.unit, dpi),
                                to_pixels(width, self.unit, dpi),
                                to_pixels(height, self.unit, dpi)), content)
        obj.placeholder = placeholder
        obj.sizing_mode = self._parse_sizing(sizing)
        if obj.sizing_mode == SizingMode.LOCKED:
            obj.locked = True
        if obj.sizing_mode == SizingMode.AUTO_FIT_CONTENT:
            LayoutEngine().fit_to_content(obj, placeholder)
        self._fitting = False
        super().__init__(obj, parent)
        self.setObjectName("textBox")

    @staticmethod
    def _parse_sizing(value: SizingMode | str) -> SizingMode:
        if isinstance(value, SizingMode):
            return value
        aliases = {
            "auto": SizingMode.AUTO_FIT_CONTENT,
            "autofit": SizingMode.AUTO_FIT_CONTENT,
            "auto_fit": SizingMode.AUTO_FIT_CONTENT,
            "free": SizingMode.FREE_RESIZE,
            "free_resize": SizingMode.FREE_RESIZE,
            "locked": SizingMode.LOCKED,
        }
        try:
            return aliases[value.lower()]
        except (AttributeError, KeyError) as exc:
            raise ValueError("sizing must be auto_fit_content, free_resize or locked") from exc

    @property
    def text(self) -> str:
        return self.obj.plain_text()

    @text.setter
    def text(self, value: str) -> None:
        self.obj.paragraphs = [Paragraph(value, default_format=self.default_format)]
        self.cursor.position = self.cursor.position.__class__(0, 0)
        self.cursor.select_none()
        self._relayout()

    def _relayout(self):
        if self._fitting:
            return super()._relayout()
        if self.obj.sizing_mode == SizingMode.AUTO_FIT_CONTENT:
            self.engine.fit_to_content(self.obj, self.obj.placeholder)
            target_width = int(self.obj.box.width())
            target_height = int(self.obj.box.height())
            if self.width() != target_width or self.height() != target_height:
                self._fitting = True
                try:
                    self.resize(target_width, target_height)
                finally:
                    self._fitting = False
        super()._relayout()

    @property
    def model(self) -> TextObject:
        """Acces au modele interne pour les integrations avancees."""
        return self.obj

    def set_text(self, value: str) -> None:
        self.text = value

    def resize_box(self, width: float, height: float) -> None:
        """Redimensionner la textbox sans manipuler directement le widget."""
        if self.obj.sizing_mode == SizingMode.LOCKED:
            return
        if self.obj.sizing_mode == SizingMode.AUTO_FIT_CONTENT:
            self.obj.sizing_mode = SizingMode.FREE_RESIZE
        self.resize(int(to_pixels(width, self.unit, self.dpi)),
                    int(to_pixels(height, self.unit, self.dpi)))

    def move_box(self, x: float, y: float) -> None:
        """Deplacer la textbox et synchroniser sa position modele."""
        if self.obj.sizing_mode == SizingMode.LOCKED:
            return
        px = to_pixels(x, self.unit, self.dpi)
        py = to_pixels(y, self.unit, self.dpi)
        self.move(int(px), int(py))
        self.obj.position = QPointF(px, py)
