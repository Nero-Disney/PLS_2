"""
Modèle de données pur pour un bloc de texte façon PowerPoint.

Aucune dépendance à un widget : Qt n'est utilisé ici que pour des types
valeur (QColor, QRectF, Qt.AlignmentFlag) qui servent aussi de types
de mesure/rendu plus bas dans la pile.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor


class VAlign(Enum):
    TOP = auto()
    MIDDLE = auto()
    BOTTOM = auto()


class Overflow(Enum):
    CLIP = auto()          # le texte qui déborde est coupé visuellement
    VISIBLE = auto()       # déborde librement hors de la boîte
    AUTOFIT_SHRINK = auto()  # réduit fontScale/lineSpacing pour rentrer (défaut PPT)
    AUTOFIT_GROW = auto()  # agrandit la boîte pour contenir le texte


@dataclass(frozen=True)
class CharFormat:
    """Format résolu d'un caractère. Immuable + hashable pour permettre
    la fusion de caractères contigus identiques en runs de rendu."""
    font_family: str = "Arial"
    font_size: float = 18.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    color: str = "#000000"          # str hex plutôt que QColor -> reste hashable
    baseline_shift: float = 0.0     # >0 exposant, <0 indice (en fraction de font_size)
    tracking: float = 0.0           # espacement additionnel entre caractères (px)
    small_caps: bool = False

    def merged(self, **overrides) -> "CharFormat":
        """Retourne une copie avec les attributs fournis remplacés."""
        return replace(self, **overrides)

    def qcolor(self) -> QColor:
        return QColor(self.color)


@dataclass
class ParagraphFormat:
    alignment: Qt.AlignmentFlag = Qt.AlignLeft
    indent_left: float = 0.0
    indent_right: float = 0.0
    indent_first_line: float = 0.0
    line_spacing: float = 1.0       # multiplicateur (1.0 = simple)
    space_before: float = 0.0
    space_after: float = 0.0
    bullet: Optional[str] = None    # caractère de puce, None = pas de puce


class Paragraph:
    """Un paragraphe : une chaîne de caractères + un format par caractère.

    Précision au caractère près : `char_formats[i]` s'applique à `text[i]`.
    Les runs de rendu (plages contiguës de même format) sont recalculés à
    la volée via `iter_runs()`, jamais stockés — ils ne sont qu'une vue
    d'optimisation pour le layout engine.
    """

    __slots__ = ("text", "char_formats", "pformat")

    def __init__(self, text: str = "", default_format: Optional[CharFormat] = None,
                 pformat: Optional[ParagraphFormat] = None):
        fmt = default_format or CharFormat()
        self.text: str = text
        self.char_formats: list[CharFormat] = [fmt] * len(text)
        self.pformat: ParagraphFormat = pformat or ParagraphFormat()

    def __len__(self) -> int:
        return len(self.text)

    def insert(self, index: int, chars: str, fmt: CharFormat) -> None:
        self.text = self.text[:index] + chars + self.text[index:]
        self.char_formats[index:index] = [fmt] * len(chars)

    def delete(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]
        del self.char_formats[start:end]

    def set_format(self, start: int, end: int, **attrs) -> None:
        for i in range(start, end):
            self.char_formats[i] = self.char_formats[i].merged(**attrs)

    def format_at(self, index: int) -> CharFormat:
        """Format du caractère à `index`, ou du dernier caractère si `index`
        est en fin de paragraphe (utile pour hériter en tapant à la fin)."""
        if not self.char_formats:
            return CharFormat()
        i = max(0, min(index, len(self.char_formats) - 1))
        return self.char_formats[i]

    def iter_runs(self):
        """Fusionne les caractères contigus de même format.
        Yields (start, end, CharFormat)."""
        if not self.text:
            return
        run_start = 0
        current = self.char_formats[0]
        for i in range(1, len(self.text)):
            if self.char_formats[i] != current:
                yield (run_start, i, current)
                run_start = i
                current = self.char_formats[i]
        yield (run_start, len(self.text), current)

    def split(self, index: int) -> "Paragraph":
        """Coupe le paragraphe à `index`, retourne la nouvelle moitié droite
        (utilisé par Entrée). La moitié droite hérite du même pformat."""
        right = Paragraph(pformat=ParagraphFormat(**self.pformat.__dict__))
        right.text = self.text[index:]
        right.char_formats = self.char_formats[index:]
        self.text = self.text[:index]
        self.char_formats = self.char_formats[:index]
        return right


class TextObject:
    """Le bloc de texte complet : contenu + boîte + comportement d'ajustement."""

    def __init__(self, box: QRectF, paragraphs: Optional[list[Paragraph]] = None):
        self.paragraphs: list[Paragraph] = paragraphs or [Paragraph()]
        self.position: QPointF = box.topLeft()
        self.box: QRectF = QRectF(0, 0, max(1.0, box.width()),
                                  max(1.0, box.height()))
        self.rotation: float = 0.0
        self.margins = (7.2, 7.2, 3.6, 3.6)  # left, right, top, bottom (pt, défauts PPT)
        self.valign: VAlign = VAlign.TOP
        self.overflow: Overflow = Overflow.AUTOFIT_SHRINK
        self.wrap: bool = True

        # Apparence de l'objet, indépendante des adorners de sélection.
        self.fill_color: Optional[str] = None
        self.fill_opacity: int = 255
        self.border_color: str = "#cccccc"
        self.border_width: float = 1.0
        self.border_style = Qt.SolidLine
        self.corner_radius: float = 0.0
        self.locked: bool = False

        # État calculé par le LayoutEngine (pas par l'utilisateur)
        self.font_scale: float = 1.0
        self.line_spacing_reduction: float = 0.0

    def plain_text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs)

    def content_rect(self) -> QRectF:
        l, r, t, b = self.margins
        return self.box.adjusted(l, t, -r, -b)
