"""Lanceur rétrocompatible de l'application finale.

L'implémentation de la textbox n'est pas définie dans ce fichier. Pour
lancer explicitement l'application, utiliser ``python final_app.py``.
"""

try:
    from .final_app import main
except ImportError:  # pragma: no cover - support script execution
    from final_app import main


if __name__ == "__main__":
    raise SystemExit(main())
