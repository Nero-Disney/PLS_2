"""Facade publique pour creer et utiliser une textbox complete."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF

try:
    from .model import Paragraph, SizingMode, TextObject
    from .view import TextObjectView
    from .layout_engine import LayoutEngine
except ImportError:  # pragma: no cover - support script execution
    from model import Paragraph, SizingMode, TextObject
    from view import TextObjectView
    from layout_engine import LayoutEngine


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
                 SizingMode.AUTO_FIT_CONTENT, parent=None):
        content = paragraphs if paragraphs is not None else [Paragraph(text)]
        obj = TextObject(QRectF(x, y, width, height), content)
        obj.placeholder = placeholder
        obj.sizing_mode = self._parse_sizing(sizing)
        if obj.sizing_mode == SizingMode.LOCKED:
            obj.locked = True
        if obj.sizing_mode == SizingMode.AUTO_FIT_CONTENT:
            LayoutEngine().fit_to_content(obj, placeholder)
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
        self.obj.paragraphs = [Paragraph(value)]
        self.cursor.position = self.cursor.position.__class__(0, 0)
        self.cursor.select_none()
        self._relayout()

    def _relayout(self):
        if self.obj.sizing_mode == SizingMode.AUTO_FIT_CONTENT:
            self.engine.fit_to_content(self.obj, self.obj.placeholder)
            self.resize(int(self.obj.box.width()), int(self.obj.box.height()))
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
        self.resize(int(width), int(height))

    def move_box(self, x: float, y: float) -> None:
        """Deplacer la textbox et synchroniser sa position modele."""
        if self.obj.sizing_mode == SizingMode.LOCKED:
            return
        self.move(int(x), int(y))
        self.obj.position.setX(float(x))
        self.obj.position.setY(float(y))
