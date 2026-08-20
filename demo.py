"""Démo minimaliste de l'éditeur de texte enrichi."""

from __future__ import annotations

import os
import sys

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication

try:
    from .model import Paragraph, TextObject
    from .view import TextObjectView
except ImportError:  # pragma: no cover - support script execution
    from model import Paragraph, TextObject
    from view import TextObjectView


def main() -> int:
    app = QApplication(sys.argv)
    obj = TextObject(QRectF(0, 0, 420, 220), [Paragraph("Bonjour PLS_2 !")])
    window = TextObjectView(obj)
    window.resize(420, 220)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
