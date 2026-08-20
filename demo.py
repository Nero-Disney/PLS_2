"""
Vue Qt minimale : peint le résultat du LayoutEngine et traduit les
événements clavier/souris en opérations sur TextCursor. La vue ne
contient aucune logique de layout ni de format — c'est un pur récepteur
d'événements + peintre du résultat déjà calculé.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget

from .model import TextObject
from .cursor import TextCursor, Position
from .layout_engine import LayoutEngine


class TextObjectView(QWidget):
    def __init__(self, obj: TextObject, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.cursor = TextCursor(obj)
        self.engine = LayoutEngine()
        self._layout_result = self.engine.layout(obj)
        self.setFocusPolicy(Qt.StrongFocus)

        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle_blink)
        self._timer.start(500)

        self.resize(int(obj.box.width()), int(obj.box.height()))

    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()

    def _relayout(self):
        self._layout_result = self.engine.layout(self.obj)
        self.update()

    # ---------- peinture ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        painter.setPen(QPen(QColor("#cccccc")))
        painter.drawRect(self.obj.box.adjusted(0, 0, -1, -1))

        content = self.obj.content_rect()
        result = self._layout_result

        v_offset = 0.0
        if self.obj.overflow.name != "AUTOFIT_SHRINK" or True:
            from .model import VAlign
            if self.obj.valign == VAlign.MIDDLE:
                v_offset = max(0.0, (content.height() - result.total_height) / 2)
            elif self.obj.valign == VAlign.BOTTOM:
                v_offset = max(0.0, content.height() - result.total_height)

        painter.save()
        painter.translate(content.left(), content.top() + v_offset)
        for pl in result.paragraph_layouts:
            pl.qlayout.draw(painter, QPointF(0, pl.y_top))
        painter.restore()

        if self.cursor.has_selection():
            self._paint_selection(painter, content, v_offset)
        elif self._blink and self.hasFocus():
            self._paint_caret(painter, content, v_offset)

    def _paint_caret(self, painter, content, v_offset):
        rect = self.engine.cursor_rect(self._layout_result,
                                        self.cursor.position.para, self.cursor.position.char)
        rect = rect.translated(content.left(), content.top() + v_offset)
        painter.fillRect(rect, QColor("#000000"))

    def _paint_selection(self, painter, content, v_offset):
        start, end = self.cursor.selection_range()
        painter.save()
        painter.translate(content.left(), content.top() + v_offset)
        brush = QBrush(QColor(100, 150, 255, 90))
        for pi in range(start.para, end.para + 1):
            pl = self._layout_result.paragraph_layouts[pi]
            a = start.char if pi == start.para else 0
            b = end.char if pi == end.para else len(pl.paragraph)
            for li in range(pl.qlayout.lineCount()):
                line = pl.qlayout.lineAt(li)
                l_start = line.textStart()
                l_end = l_start + line.textLength()
                sel_a = max(a, l_start)
                sel_b = min(b, l_end)
                if sel_a < sel_b:
                    x1 = line.cursorToX(sel_a)
                    x2 = line.cursorToX(sel_b)
                    y = pl.y_top + line.position().y()
                    painter.fillRect(QRectF(x1, y, x2 - x1, line.height()), brush)
        painter.restore()

    # ---------- clavier ----------

    def keyPressEvent(self, event):
        text = event.text()
        key = event.key()

        if key == Qt.Key_Backspace:
            self.cursor.backspace()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self.cursor.insert_paragraph_break()
        elif key == Qt.Key_Left:
            self._move(-1, extend=event.modifiers() & Qt.ShiftModifier)
        elif key == Qt.Key_Right:
            self._move(1, extend=event.modifiers() & Qt.ShiftModifier)
        elif key == Qt.Key_B and event.modifiers() & Qt.ControlModifier:
            cur = self.cursor.current_format()
            self.cursor.apply_format_to_selection_or_pending(bold=not cur.bold)
        elif key == Qt.Key_I and event.modifiers() & Qt.ControlModifier:
            cur = self.cursor.current_format()
            self.cursor.apply_format_to_selection_or_pending(italic=not cur.italic)
        elif text and text.isprintable():
            self.cursor.insert_text(text)
        else:
            return super().keyPressEvent(event)

        self._relayout()

    def _move(self, delta: int, extend: bool):
        pos = self.cursor.position
        p = self.obj.paragraphs[pos.para]
        new_char = pos.char + delta
        new_para = pos.para
        if new_char < 0:
            if pos.para > 0:
                new_para -= 1
                new_char = len(self.obj.paragraphs[new_para])
            else:
                new_char = 0
        elif new_char > len(p):
            if pos.para < len(self.obj.paragraphs) - 1:
                new_para += 1
                new_char = 0
            else:
                new_char = len(p)
        new_pos = Position(new_para, new_char)
        if extend:
            if self.cursor.anchor is None:
                self.cursor.anchor = Position(pos.para, pos.char)
            self.cursor.position = new_pos
        else:
            self.cursor.select_none()
            self.cursor.position = new_pos

    # ---------- souris ----------

    def mousePressEvent(self, event):
        content = self.obj.content_rect()
        local = event.position() - content.topLeft()
        para, char = self.engine.hit_test(self._layout_result, local)
        self.cursor.select_none()
        self.cursor.position = Position(para, char)
        self.setFocus()
        self.update()

    def resizeEvent(self, event):
        self.obj.box = QRectF(0, 0, self.width(), self.height())
        self._relayout()
