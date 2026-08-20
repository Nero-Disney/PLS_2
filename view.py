"""
Vue Qt minimale : peint le résultat du LayoutEngine et traduit les
événements clavier/souris en opérations sur TextCursor. La vue ne
contient aucune logique de layout ni de format — c'est un pur récepteur
d'événements + peintre du résultat déjà calculé.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTransform
from PySide6.QtWidgets import QWidget, QApplication

try:
    from .model import TextObject, Overflow, VAlign
    from .cursor import TextCursor, Position
    from .layout_engine import LayoutEngine
except ImportError:  # pragma: no cover - support script execution
    from model import TextObject, Overflow, VAlign
    from cursor import TextCursor, Position
    from layout_engine import LayoutEngine


class TextObjectView(QWidget):
    HANDLE_SIZE = 8.0
    MIN_WIDTH = 40.0
    MIN_HEIGHT = 30.0

    def __init__(self, obj: TextObject, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.cursor = TextCursor(obj)
        self.engine = LayoutEngine()
        self._layout_result = self.engine.layout(obj)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        self.setMouseTracking(True)
        self.setAccessibleName("Text box")
        self.setAccessibleDescription("Editable text box with resize and rotation handles")

        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle_blink)
        self._timer.start(500)

        self._selected = True
        self._edit_mode = False
        self._drag_mode = None
        self._drag_handle = None
        self._drag_start = QPointF()
        self._drag_geometry = None
        self._rotation_start = 0.0
        self._rotation_origin = QPointF()

        self.resize(int(obj.box.width()), int(obj.box.height()))
        self.move(int(obj.position.x()), int(obj.position.y()))

    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()

    def _relayout(self):
        self._layout_result = self.engine.layout(self.obj)
        self.update()

    def _vertical_offset(self, result, content):
        """Retourne le décalage vertical à appliquer au rendu.

        En mode AUTOFIT_SHRINK, le moteur a déjà ajusté la taille du texte pour
        qu'il tienne dans la boîte ; on ne doit pas appliquer un second
        centrage/décalage vertical dans ce cas.
        """
        if self.obj.overflow == Overflow.AUTOFIT_SHRINK:
            return 0.0
        if self.obj.valign == VAlign.MIDDLE:
            return max(0.0, (content.height() - result.total_height) / 2)
        if self.obj.valign == VAlign.BOTTOM:
            return max(0.0, content.height() - result.total_height)
        return 0.0

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)

    # ---------- peinture ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        painter.save()
        self._apply_object_transform(painter)
        if self.obj.fill_color:
            fill = QColor(self.obj.fill_color)
            fill.setAlpha(max(0, min(255, self.obj.fill_opacity)))
            painter.fillRect(self.obj.box, fill)
        painter.setPen(QPen(QColor(self.obj.border_color), self.obj.border_width,
                            self.obj.border_style))
        painter.setBrush(Qt.NoBrush)
        if self.obj.overflow == Overflow.CLIP:
            painter.setClipRect(self.obj.box)
        if self.obj.corner_radius > 0:
            painter.drawRoundedRect(self.obj.box, self.obj.corner_radius,
                                    self.obj.corner_radius)
        else:
            painter.drawRect(self.obj.box.adjusted(0, 0, -1, -1))

        content = self.obj.content_rect()
        result = self._layout_result
        v_offset = self._vertical_offset(result, content)

        painter.save()
        painter.translate(content.left(), content.top() + v_offset)
        for pl in result.paragraph_layouts:
            pl.qlayout.draw(painter, QPointF(0, pl.y_top))
        painter.restore()

        if self.cursor.has_selection():
            self._paint_selection(painter, content, v_offset)
        elif self._edit_mode and self._blink and self.hasFocus():
            self._paint_caret(painter, content, v_offset)
        painter.restore()

        if self._selected:
            painter.save()
            self._apply_object_transform(painter)
            self._paint_bounding_box(painter)
            painter.restore()

    def _apply_object_transform(self, painter):
        center = self.obj.box.center()
        painter.translate(center)
        painter.rotate(self.obj.rotation)
        painter.translate(-center)

    def _local_point(self, point):
        center = self.obj.box.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(self.obj.rotation)
        transform.translate(-center.x(), -center.y())
        return transform.inverted()[0].map(point)

    def _view_point(self, point):
        center = self.obj.box.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(self.obj.rotation)
        transform.translate(-center.x(), -center.y())
        return transform.map(point)

    def _handle_rects(self):
        half = self.HANDLE_SIZE / 2
        box = QRectF(0, 0, self.width(), self.height())
        points = {
            "top_left": box.topLeft(),
            "top": QPointF(box.center().x(), box.top()),
            "top_right": box.topRight(),
            "right": QPointF(box.right(), box.center().y()),
            "bottom_right": box.bottomRight(),
            "bottom": QPointF(box.center().x(), box.bottom()),
            "bottom_left": box.bottomLeft(),
            "left": QPointF(box.left(), box.center().y()),
            "rotate": QPointF(box.center().x(), box.top() + 12.0),
        }
        return {
            name: QRectF(point.x() - half, point.y() - half,
                         self.HANDLE_SIZE, self.HANDLE_SIZE)
            for name, point in points.items()
        }

    def _paint_bounding_box(self, painter):
        painter.save()
        painter.setPen(QPen(QColor("#2878d4"), 1, Qt.DashLine))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setPen(QPen(QColor("#2878d4")))
        painter.setBrush(QBrush(QColor("#ffffff")))
        for rect in self._handle_rects().values():
            painter.drawRect(rect)
        rotate = self._handle_rects()["rotate"].center()
        painter.drawLine(QPointF(self.width() / 2, 0), rotate)
        painter.restore()

    def _handle_at(self, point):
        for name, rect in self._handle_rects().items():
            if rect.contains(point):
                return name
        return None

    def _cursor_for_handle(self, handle):
        if handle == "rotate":
            return Qt.OpenHandCursor
        if handle in ("top_left", "bottom_right"):
            return Qt.SizeFDiagCursor
        if handle in ("top_right", "bottom_left"):
            return Qt.SizeBDiagCursor
        if handle in ("top", "bottom"):
            return Qt.SizeVerCursor
        if handle in ("left", "right"):
            return Qt.SizeHorCursor
        return Qt.ArrowCursor

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
                l_start = max(0, line.textStart() - pl.text_offset)
                l_end = min(len(pl.paragraph),
                            l_start + line.textLength() - pl.text_offset)
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
        modifiers = event.modifiers()

        if modifiers & Qt.ControlModifier and key == Qt.Key_Z:
            if self.cursor.undo():
                self._relayout()
            return
        if modifiers & Qt.ControlModifier and key == Qt.Key_Y:
            if self.cursor.redo():
                self._relayout()
            return
        if modifiers & Qt.ControlModifier and key == Qt.Key_A:
            self.cursor.set_selection(Position(0, 0), Position(
                len(self.obj.paragraphs) - 1,
                len(self.obj.paragraphs[-1])))
            self.update()
            return
        if modifiers & Qt.ControlModifier and key in (Qt.Key_C, Qt.Key_X):
            QApplication.clipboard().setText(self.cursor.selected_text())
            if key == Qt.Key_X and self.cursor.has_selection():
                self.cursor.backspace()
                self._relayout()
            return
        if modifiers & Qt.ControlModifier and key == Qt.Key_V:
            self.cursor.insert_text(QApplication.clipboard().text())
            self._relayout()
            return

        if key == Qt.Key_Escape:
            self._edit_mode = False
            self.cursor.select_none()
            self.clearFocus()
            self.update()
            return
        if key == Qt.Key_Backspace:
            self.cursor.backspace()
        elif key == Qt.Key_Delete:
            self._delete_forward()
        elif key == Qt.Key_Home:
            self._move_to_line_edge(False, bool(event.modifiers() & Qt.ShiftModifier))
        elif key == Qt.Key_End:
            self._move_to_line_edge(True, bool(event.modifiers() & Qt.ShiftModifier))
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

    def _delete_forward(self):
        if self.cursor.has_selection():
            self.cursor.backspace()
            return
        self._move(1, extend=True)
        if self.cursor.has_selection():
            self.cursor.backspace()

    def _move_to_line_edge(self, end, extend):
        pos = self.cursor.position
        new_pos = Position(pos.para, len(self.obj.paragraphs[pos.para]) if end else 0)
        if extend:
            if self.cursor.anchor is None:
                self.cursor.anchor = Position(pos.para, pos.char)
            self.cursor.position = new_pos
        else:
            self.cursor.select_none()
            self.cursor.position = new_pos

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
        point = event.position()
        local_point = self._local_point(point)
        handle = self._handle_at(local_point) if self._selected else None
        if handle:
            if self.obj.locked:
                event.accept()
                return
            self._drag_mode = "resize"
            self._drag_handle = handle
            self._drag_start = point
            self._drag_geometry = self.geometry()
            if handle == "rotate":
                self._drag_mode = "rotate"
                center = self._local_point(self.obj.box.center())
                self._rotation_origin = center
                self._rotation_start = math.degrees(math.atan2(
                    local_point.y() - center.y(), local_point.x() - center.x()))
            self.grabMouse()
            event.accept()
            return

        border = self.obj.box.adjusted(3, 3, -3, -3)
        if self._selected and self.obj.box.contains(local_point) and not border.contains(local_point):
            self._drag_mode = "move"
            self._drag_start = point
            self._drag_geometry = self.geometry()
            self.grabMouse()
            event.accept()
            return

        content = self.obj.content_rect()
        local = local_point - content.topLeft()
        para, char = self.engine.hit_test(self._layout_result,
                                          local - QPointF(0, self._vertical_offset(
                                              self._layout_result, content)))
        self.cursor.select_none()
        self.cursor.position = Position(para, char)
        self._drag_mode = "text"
        self._drag_start = point
        self._edit_mode = True
        self.setFocus()
        self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        point = event.position()
        local_point = self._local_point(point)
        if self._drag_mode == "text":
            content = self.obj.content_rect()
            para, char = self.engine.hit_test(self._layout_result,
                                              local_point - content.topLeft() - QPointF(
                                                  0, self._vertical_offset(
                                                      self._layout_result, content)))
            if self.cursor.anchor is None:
                self.cursor.anchor = Position(self.cursor.position.para,
                                              self.cursor.position.char)
            self.cursor.position = Position(para, char)
            self.update()
        elif self._drag_mode == "move":
            self._move_geometry(point - self._drag_start)
        elif self._drag_mode == "resize":
            self._resize_geometry(local_point - self._local_point(self._drag_start),
                                  event.modifiers())
        elif self._drag_mode == "rotate":
            center = self._local_point(self.obj.box.center())
            current = math.degrees(math.atan2(local_point.y() - center.y(),
                                               local_point.x() - center.x()))
            angle = self.obj.rotation + current - self._rotation_start
            if event.modifiers() & Qt.ShiftModifier:
                angle = round(angle / 15.0) * 15.0
            self.obj.rotation = angle % 360.0
            self.update()
        else:
            handle = self._handle_at(local_point) if self._selected else None
            self.setCursor(self._cursor_for_handle(handle))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_mode in ("move", "resize", "rotate"):
            self.releaseMouse()
        self._drag_mode = None
        self._drag_handle = None
        self._drag_geometry = None
        self.setCursor(self._cursor_for_handle(self._handle_at(
            self._local_point(event.position())) if self._selected else None))
        event.accept()

    def _move_geometry(self, delta):
        geometry = self._drag_geometry.translated(int(delta.x()), int(delta.y()))
        self.setGeometry(geometry)
        self.obj.position = QPointF(geometry.x(), geometry.y())

    def _resize_geometry(self, delta, modifiers):
        geometry = QRectF(self._drag_geometry)
        handle = self._drag_handle
        if "left" in handle:
            geometry.setLeft(min(geometry.right() - self.MIN_WIDTH,
                                 geometry.left() + delta.x()))
        if "right" in handle:
            geometry.setRight(max(geometry.left() + self.MIN_WIDTH,
                                  geometry.right() + delta.x()))
        if "top" in handle:
            geometry.setTop(min(geometry.bottom() - self.MIN_HEIGHT,
                                geometry.top() + delta.y()))
        if "bottom" in handle:
            geometry.setBottom(max(geometry.top() + self.MIN_HEIGHT,
                                   geometry.bottom() + delta.y()))

        if modifiers & Qt.ShiftModifier:
            ratio = self._drag_geometry.width() / max(1.0, self._drag_geometry.height())
            if "left" in handle or "right" in handle:
                geometry.setHeight(max(self.MIN_HEIGHT, geometry.width() / ratio))
            else:
                geometry.setWidth(max(self.MIN_WIDTH, geometry.height() * ratio))
            if "top" in handle:
                geometry.moveTop(self._drag_geometry.bottom() - geometry.height())
            if "left" in handle:
                geometry.moveLeft(self._drag_geometry.right() - geometry.width())

        self.setGeometry(geometry.toRect())

    def resizeEvent(self, event):
        self.obj.box = QRectF(0, 0, self.width(), self.height())
        self.obj.position = QPointF(self.x(), self.y())
        self._relayout()
