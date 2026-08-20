"""
Curseur et sélection pour TextObject.

Reproduit le comportement PowerPoint autour du formatage :
- Taper sans sélection hérite du format du caractère précédent.
- Appliquer un format sans sélection ne change rien au texte existant,
  seulement le "format en attente" pour la prochaine frappe.
- Entrée hérite le pformat du paragraphe courant pour le nouveau paragraphe.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from typing import Optional

try:
    from .model import TextObject, Paragraph, CharFormat, ParagraphFormat
except ImportError:  # pragma: no cover - support script execution
    from model import TextObject, Paragraph, CharFormat, ParagraphFormat


@dataclass
class Position:
    para: int
    char: int

    def __le__(self, other: "Position") -> bool:
        return (self.para, self.char) <= (other.para, other.char)

    def __lt__(self, other: "Position") -> bool:
        return (self.para, self.char) < (other.para, other.char)


class TextCursor:
    def __init__(self, obj: TextObject):
        self.obj = obj
        self.position = Position(0, 0)
        self.anchor: Optional[Position] = None   # None => pas de sélection
        # Format explicitement choisi par l'utilisateur (ex: clic sur "Gras"
        # sans sélection) en attente d'être appliqué à la prochaine frappe.
        self.pending_format: Optional[CharFormat] = None
        self._undo_stack = []
        self._redo_stack = []

    def _snapshot(self):
        return deepcopy((self.obj.paragraphs, self.position, self.anchor,
                         self.pending_format))

    def _record_edit(self):
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()

    def _restore(self, snapshot):
        paragraphs, position, anchor, pending = deepcopy(snapshot)
        self.obj.paragraphs = paragraphs
        self.position = position
        self.anchor = anchor
        self.pending_format = pending

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())
        return True

    # ---------- sélection ----------

    def has_selection(self) -> bool:
        return self.anchor is not None and self.anchor != self.position

    def selection_range(self) -> tuple[Position, Position]:
        assert self.has_selection()
        return (self.anchor, self.position) if self.anchor < self.position \
            else (self.position, self.anchor)

    def select_none(self) -> None:
        self.anchor = None

    def set_selection(self, anchor: Position, pos: Position) -> None:
        self.anchor = anchor
        self.position = pos

    def selected_text(self) -> str:
        if not self.has_selection():
            return ""
        start, end = self.selection_range()
        parts = []
        for pi in range(start.para, end.para + 1):
            paragraph = self.obj.paragraphs[pi]
            a = start.char if pi == start.para else 0
            b = end.char if pi == end.para else len(paragraph)
            parts.append(paragraph.text[a:b])
        return "\n".join(parts)

    # ---------- format courant (pour la barre d'outils) ----------

    def current_format(self) -> CharFormat:
        """Format à afficher dans la barre d'outils : celui de la sélection
        si homogène, celui du pending_format si actif, sinon celui hérité
        de la position du curseur."""
        if self.pending_format is not None and not self.has_selection():
            return self.pending_format
        if self.has_selection():
            start, end = self.selection_range()
            fmts = self._formats_in_range(start, end)
            first = fmts[0]
            if all(f == first for f in fmts):
                return first
            return first  # mixte : on renvoie le premier (l'UI peut afficher "mixte")
        return self._inherited_format_at(self.position)

    def _formats_in_range(self, start: Position, end: Position) -> list[CharFormat]:
        out = []
        for pi in range(start.para, end.para + 1):
            p = self.obj.paragraphs[pi]
            a = start.char if pi == start.para else 0
            b = end.char if pi == end.para else len(p)
            out.extend(p.char_formats[a:b])
        return out or [CharFormat()]

    def _inherited_format_at(self, pos: Position) -> CharFormat:
        """Format hérité pour taper à `pos` : celui du caractère précédent,
        ou du caractère suivant si en tout début de paragraphe, ou défaut."""
        p = self.obj.paragraphs[pos.para]
        if pos.char > 0:
            return p.format_at(pos.char - 1)
        if len(p) > 0:
            return p.format_at(0)
        # paragraphe vide : hérite du paragraphe précédent s'il existe
        if pos.para > 0:
            prev = self.obj.paragraphs[pos.para - 1]
            if len(prev) > 0:
                return prev.format_at(len(prev) - 1)
        return CharFormat()

    # ---------- édition ----------

    def apply_format_to_selection_or_pending(self, **attrs) -> None:
        """Bouton 'Gras' etc. Comportement PowerPoint : si sélection ->
        applique immédiatement au texte sélectionné. Sinon -> mémorise
        dans pending_format pour la prochaine frappe."""
        if self.has_selection():
            start, end = self.selection_range()
            self._record_edit()
            for pi in range(start.para, end.para + 1):
                p = self.obj.paragraphs[pi]
                a = start.char if pi == start.para else 0
                b = end.char if pi == end.para else len(p)
                p.set_format(a, b, **attrs)
        else:
            base = self.pending_format or self._inherited_format_at(self.position)
            self.pending_format = base.merged(**attrs)

    def insert_text(self, chars: str) -> None:
        if not chars:
            return
        self._record_edit()
        if self.has_selection():
            self._delete_selection()
        fmt = self.pending_format or self._inherited_format_at(self.position)
        parts = chars.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        paragraph = self.obj.paragraphs[self.position.para]
        paragraph.insert(self.position.char, parts[0], fmt)
        self.position.char += len(parts[0])
        for part in parts[1:]:
            right = paragraph.split(self.position.char)
            right.pformat = ParagraphFormat(**paragraph.pformat.__dict__)
            self.obj.paragraphs.insert(self.position.para + 1, right)
            self.position = Position(self.position.para + 1, 0)
            paragraph = right
            paragraph.insert(0, part, fmt)
            self.position.char = len(part)
        self.pending_format = None  # consommé

    def insert_paragraph_break(self) -> None:
        self._record_edit()
        if self.has_selection():
            self._delete_selection()
        p = self.obj.paragraphs[self.position.para]
        right = p.split(self.position.char)
        # hérite explicitement le pformat courant pour le nouveau paragraphe
        right.pformat = ParagraphFormat(**p.pformat.__dict__)
        self.obj.paragraphs.insert(self.position.para + 1, right)
        self.position = Position(self.position.para + 1, 0)
        self.pending_format = None

    def backspace(self) -> None:
        if not self.has_selection() and self.position.char == 0 and self.position.para == 0:
            return
        self._record_edit()
        if self.has_selection():
            self._delete_selection()
            return
        pos = self.position
        if pos.char > 0:
            p = self.obj.paragraphs[pos.para]
            p.delete(pos.char - 1, pos.char)
            self.position.char -= 1
        elif pos.para > 0:
            prev = self.obj.paragraphs[pos.para - 1]
            cur = self.obj.paragraphs.pop(pos.para)
            join_at = len(prev)
            prev.text += cur.text
            prev.char_formats += cur.char_formats
            self.position = Position(pos.para - 1, join_at)

    def _delete_selection(self) -> None:
        start, end = self.selection_range()
        if start.para == end.para:
            self.obj.paragraphs[start.para].delete(start.char, end.char)
        else:
            first = self.obj.paragraphs[start.para]
            last = self.obj.paragraphs[end.para]
            first.delete(start.char, len(first))
            tail_text = last.text[end.char:]
            tail_formats = last.char_formats[end.char:]
            first.text += tail_text
            first.char_formats += tail_formats
            del self.obj.paragraphs[start.para + 1: end.para + 1]
        self.position = start
        self.anchor = None
