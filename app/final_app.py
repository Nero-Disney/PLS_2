"""Application finale de validation de la textbox PLS_2.

Ce module est une couche d'exécution uniquement : l'implémentation de la
textbox vit dans le package editor/.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from PySide6.QtWidgets import QApplication

try:
    from PLS_2.editor.textbox import TextBox
except ImportError:  # pragma: no cover - support script execution
    try:
        from editor.textbox import TextBox
    except ImportError:  # pragma: no cover
        from ..editor.textbox import TextBox


DEFAULT_WIDTH = 420
DEFAULT_HEIGHT = 220


def create_demo_object() -> TextBox:
    """Créer le contenu initial utilisé uniquement par l'application finale."""
    return TextBox(
        text="Bonjour PLS_2 !",
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
    )


def create_application(argv=None):
    """Créer l'application Qt et sa textbox de démonstration."""
    app = QApplication.instance() or QApplication(argv or sys.argv)
    window = create_demo_object()
    window.setWindowTitle("PLS_2 - Textbox complète")
    return app, window


def main(argv=None) -> int:
    app, window = create_application(argv)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
