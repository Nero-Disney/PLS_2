"""Direct printing and PDF export for label documents."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, QSizeF
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtGui import QPageLayout, QPageSize

try:
    from .label_design import LabelDocument
    from .units import Unit, to_pixels
except ImportError:  # pragma: no cover
    from label_design import LabelDocument
    from units import Unit, to_pixels


class LabelPrinter:
    """Render a headless LabelDocument to a printer or PDF target."""

    def __init__(self, document: LabelDocument):
        self.document = document

    def configure(self, printer: QPrinter) -> QPrinter:
        """Configure the target without changing the document geometry."""
        printer.setFullPage(True)
        spec = self.document.print_spec
        if spec is not None:
            printer.setResolution(round(spec.dpi))
            if spec.orientation.value == "landscape":
                printer.setPageOrientation(QPageLayout.Landscape)
            if spec.color_mode.value == "monochrome":
                printer.setColorMode(QPrinter.GrayScale)
        if self.document.unit == Unit.MILLIMETER:
            width = self.document.width
            height = self.document.height
            printer.setPageSize(QPageSize(QSizeF(width, height),
                                          QPageSize.Millimeter))
        elif self.document.unit == Unit.POINT:
            printer.setPageSize(QPageSize(QSizeF(self.document.width,
                                                 self.document.height),
                                          QPageSize.Point))
        else:
            printer.setPageSize(QPageSize(QSizeF(
                self.document.width * 25.4 / self.document.dpi,
                self.document.height * 25.4 / self.document.dpi),
                QPageSize.Millimeter))
        return printer

    def render(self, painter: QPainter, target_dpi: Optional[float] = None) -> None:
        """Render fields in document coordinates onto an active painter."""
        dpi = target_dpi or self.document.dpi
        painter.save()
        painter.setPen(QColor("#000000"))
        for field in self.document.fields:
            if not field.visible:
                continue
            x = to_pixels(field.x, self.document.unit, dpi)
            y = to_pixels(field.y, self.document.unit, dpi)
            width = to_pixels(field.width, self.document.unit, dpi)
            height = to_pixels(field.height, self.document.unit, dpi)
            rect = QRectF(x, y, width, height)
            painter.save()
            painter.translate(rect.center())
            painter.rotate(field.rotation)
            painter.translate(-rect.center())
            painter.setFont(QFont(self.document.theme.style_for(field.field_type).font_family,
                                  max(1, round(self.document.theme.style_for(
                                      field.field_type).font_size))))
            painter.drawText(rect, field.display_value())
            painter.restore()
        for graphic in self.document.graphics:
            if not graphic.visible:
                continue
            x = to_pixels(graphic.x, self.document.unit, dpi)
            y = to_pixels(graphic.y, self.document.unit, dpi)
            width = to_pixels(graphic.width, self.document.unit, dpi)
            height = to_pixels(graphic.height, self.document.unit, dpi)
            rect = QRectF(x, y, width, height)
            painter.save()
            painter.setPen(QColor(graphic.foreground))
            painter.setBrush(QColor(graphic.background))
            painter.drawRect(rect)
            payload = getattr(graphic, "payload", "") or graphic.display_value()
            if payload:
                painter.setBrush(QColor(graphic.foreground))
                painter.setFont(QFont("Arial", max(1, round(height / 8))))
                painter.drawText(rect, payload)
            painter.restore()
        painter.restore()

    def _check_printable(self) -> bool:
        return self.document.validate().valid

    def print_direct(self, printer: Optional[QPrinter] = None) -> bool:
        """Print directly, without showing a dialog."""
        if not self._check_printable():
            return False
        target = self.configure(printer or QPrinter(QPrinter.HighResolution))
        painter = QPainter(target)
        try:
            self.render(painter, target.logicalDpiX())
            if self.document.print_spec is not None:
                from .label_printing import PrintStatus
                self.document.print_spec.status = PrintStatus.PRINTED
            return True
        finally:
            painter.end()

    def print_with_dialog(self, parent=None) -> bool:
        """Show the native printer dialog, then print when accepted."""
        if not self._check_printable():
            return False
        target = self.configure(QPrinter(QPrinter.HighResolution))
        dialog = QPrintDialog(target, parent)
        if dialog.exec() != QPrintDialog.Accepted:
            return False
        painter = QPainter(target)
        try:
            self.render(painter, target.logicalDpiX())
            return True
        finally:
            painter.end()

    def export_pdf(self, path: str) -> str:
        """Export one label to a PDF file using the same print renderer."""
        if not self._check_printable():
            raise ValueError("label contains blocking validation errors")
        target = QPrinter(QPrinter.HighResolution)
        target.setOutputFormat(QPrinter.PdfFormat)
        target.setOutputFileName(path)
        self.configure(target)
        painter = QPainter(target)
        try:
            self.render(painter, target.logicalDpiX())
        finally:
            painter.end()
        return path


def print_document(document: LabelDocument, parent=None,
                   direct: bool = False) -> bool:
    """Convenience API for direct or dialog-based printing."""
    printer = LabelPrinter(document)
    return printer.print_direct() if direct else printer.print_with_dialog(parent)
