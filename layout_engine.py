"""
Moteur de layout : transforme un TextObject en géométrie de lignes prête
à peindre. Qt sert ici uniquement à la mesure typographique (QTextLayout,
QFontMetricsF) — aucune notion de widget n'y entre.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import (
    QFont, QTextLayout, QTextOption, QTextLine,
    QTextCharFormat, QColor, QFontMetricsF,
)

try:
    from .model import TextObject, Paragraph, VAlign, Overflow
except ImportError:  # pragma: no cover - support script execution
    from model import TextObject, Paragraph, VAlign, Overflow


def _qfont_default(scale: float) -> QFont:
    f = QFont("Arial")
    f.setPointSizeF(max(1.0, 18.0 * scale))
    return f


def _qfont(fmt, scale: float) -> QFont:
    f = QFont(fmt.font_family)
    f.setPointSizeF(max(1.0, fmt.font_size * scale))
    f.setBold(fmt.bold)
    f.setItalic(fmt.italic)
    f.setUnderline(fmt.underline)
    f.setStrikeOut(fmt.strikethrough)
    if fmt.tracking:
        f.setLetterSpacing(QFont.AbsoluteSpacing, fmt.tracking * scale)
    if fmt.small_caps:
        f.setCapitalization(QFont.SmallCaps)
    return f


@dataclass
class ParagraphLayout:
    paragraph: Paragraph
    qlayout: QTextLayout
    y_top: float          # position verticale (dans content_rect) du haut du paragraphe
    height: float
    text_offset: int = 0  # caractères décoratifs préfixés (puce)


@dataclass
class LayoutResult:
    paragraph_layouts: list[ParagraphLayout]
    total_height: float
    font_scale: float
    fits: bool


class LayoutEngine:
    MIN_SCALE = 0.25
    SCALE_STEP = 0.9

    def layout(self, obj: TextObject) -> LayoutResult:
        content = obj.content_rect()
        width = content.width() if obj.wrap else 1_000_000.0

        if obj.overflow == Overflow.AUTOFIT_SHRINK:
            scale = 1.0
            while True:
                result = self._layout_at_scale(obj, width, content.height(), scale)
                if result.fits or scale <= self.MIN_SCALE:
                    obj.font_scale = scale
                    return result
                scale *= self.SCALE_STEP
        else:
            result = self._layout_at_scale(obj, width, content.height(), 1.0)
            if obj.overflow == Overflow.AUTOFIT_GROW and not result.fits:
                l, r, t, b = obj.margins
                obj.box.setHeight(max(obj.box.height(), result.total_height + t + b))
                content = obj.content_rect()
                result = self._layout_at_scale(obj, width, content.height(), 1.0)
            obj.font_scale = 1.0
            return result

    def _layout_at_scale(self, obj: TextObject, width: float,
                          max_height: float, scale: float) -> LayoutResult:
        paragraph_layouts: list[ParagraphLayout] = []
        y = 0.0

        for para in obj.paragraphs:
            y += para.pformat.space_before * scale

            prefix = (para.pformat.bullet + " ") if para.pformat.bullet else ""
            display_text = prefix + (para.text if para.text else " ")
            text_offset = len(prefix)
            qlayout = QTextLayout(display_text)
            option = QTextOption(para.pformat.alignment)
            option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere
                                if width < 1_000_000 else QTextOption.NoWrap)
            qlayout.setTextOption(option)

            formats = []
            max_size = 0.0
            dominant_fmt = para.char_formats[0] if para.char_formats else None
            if para.text:
                for start, end, fmt in para.iter_runs():
                    cf = QTextCharFormat()
                    cf.setFont(_qfont(fmt, scale))
                    cf.setForeground(QColor(fmt.color))
                    if fmt.baseline_shift > 0:
                        cf.setVerticalAlignment(QTextCharFormat.AlignSuperScript)
                    elif fmt.baseline_shift < 0:
                        cf.setVerticalAlignment(QTextCharFormat.AlignSubScript)
                    formats.append(QTextLayout.FormatRange(
                        start=start + text_offset, length=end - start, format=cf))
                    if fmt.font_size > max_size:
                        max_size, dominant_fmt = fmt.font_size, fmt
            qlayout.setFormats(formats)
            # QTextLine.height()/ascent() suivent la police PAR DEFAUT du
            # QTextLayout, pas les formats par caractère (qui ne pilotent
            # que le rendu des glyphes). Sans ceci, l'autofit n'a aucun
            # effet sur la hauteur mesurée -> on fixe la police dominante
            # (la plus grande taille du paragraphe) à l'échelle courante.
            qlayout.setFont(_qfont(dominant_fmt, scale) if dominant_fmt else _qfont_default(scale))

            indent_l = para.pformat.indent_left
            indent_first = para.pformat.indent_first_line
            line_spacing = para.pformat.line_spacing * (1.0 - obj.line_spacing_reduction)

            qlayout.beginLayout()
            para_top = y
            first_line = True
            while True:
                line = qlayout.createLine()
                if not line.isValid():
                    break
                avail = max(1.0, width - indent_l - (indent_first if first_line else 0.0)
                            - para.pformat.indent_right)
                line.setLineWidth(avail)
                line_x = indent_l + (indent_first if first_line else 0.0)
                line.setPosition(QPointF(line_x, y - para_top))
                y += line.height() * line_spacing
                first_line = False
            qlayout.endLayout()

            y += para.pformat.space_after * scale
            paragraph_layouts.append(ParagraphLayout(
                paragraph=para, qlayout=qlayout, y_top=para_top, height=y - para_top,
                text_offset=text_offset,
            ))

        total_height = y
        fits = total_height <= max_height + 0.5  # tolérance d'arrondi
        return LayoutResult(paragraph_layouts, total_height, scale, fits)

    # ---------- hit-testing (pour placer le curseur au clic) ----------

    def hit_test(self, result: LayoutResult, point: QPointF):
        """Retourne (paragraph_index, char_index) le plus proche de `point`
        (coordonnées relatives au content_rect)."""
        for pi, pl in enumerate(result.paragraph_layouts):
            local_y = point.y() - pl.y_top
            if 0 <= local_y <= pl.height or pi == len(result.paragraph_layouts) - 1:
                for li in range(pl.qlayout.lineCount()):
                    line: QTextLine = pl.qlayout.lineAt(li)
                    ly = line.position().y()
                    if local_y <= ly + line.height() or li == pl.qlayout.lineCount() - 1:
                        char = line.xToCursor(point.x() - line.position().x())
                        if isinstance(char, tuple):
                            char = char[0]
                        char = max(pl.text_offset,
                                   min(pl.text_offset + len(pl.paragraph), char))
                        return (pi, char - pl.text_offset)
        return (0, 0)

    def cursor_rect(self, result: LayoutResult, para: int, char: int) -> QRectF:
        """Rectangle du caret pour (para, char), coordonnées content_rect."""
        pl = result.paragraph_layouts[para]
        char = max(0, min(len(pl.paragraph), char))
        display_char = char + pl.text_offset
        line = pl.qlayout.lineForTextPosition(display_char)
        if not line.isValid():
            line = pl.qlayout.lineAt(max(0, pl.qlayout.lineCount() - 1))
        x = line.cursorToX(display_char)[0] if isinstance(line.cursorToX(display_char), tuple) else line.cursorToX(display_char)
        y = pl.y_top + line.position().y()
        return QRectF(x, y, 1.5, line.height())
