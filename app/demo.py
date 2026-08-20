"""Lanceur rétrocompatible de l'application finale.

L'implémentation de la textbox n'est pas définie dans ce fichier. Pour
lancer explicitement l'application, utiliser ``python app/final_app.py``.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

try:
    from PLS_2.app.final_app import main
except ImportError:  # pragma: no cover - support script execution
    try:
        from app.final_app import main
    except ImportError:  # pragma: no cover
        from .final_app import main


if __name__ == "__main__":
    raise SystemExit(main())
