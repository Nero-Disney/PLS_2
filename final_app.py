"""Application finale de validation de la textbox PLS_2.

Ce module est une couche d'exécution uniquement : l'implémentation de la
textbox reste dans model.py, cursor.py, layout_engine.py et view.py.
"""

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


DEFAULT_WIDTH = 420
DEFAULT_HEIGHT = 220


def create_demo_object() -> TextObject:
    """Créer le contenu initial utilisé uniquement par l'application finale."""
    return TextObject(
        QRectF(0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT),
        [Paragraph("Bonjour PLS_2 !")],
    )


def create_application(argv=None):
    """Créer l'application Qt et sa textbox de démonstration."""
    app = QApplication.instance() or QApplication(argv or sys.argv)
    window = TextObjectView(create_demo_object())
    window.setWindowTitle("PLS_2 - Textbox complète")
    window.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
    return app, window


def main(argv=None) -> int:
    app, window = create_application(argv)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
