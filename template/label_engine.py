"""Helpers for printable label templates and compact prefab serialization.

This module keeps the architecture aligned with the rest of the project: a
headless, data-oriented model for tags and printed labels, without depending on
Qt widgets. It exposes the building blocks needed to serialize templates,
resolve data bindings, impose layout constraints and arrange mixed templates on a
page.
"""

from __future__ import annotations

import json
import math
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen


class BoxEdge(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER_H = "center_h"
    CENTER_V = "center_v"


class Alignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class OptimizedElement:
    """Ultra-lightweight label node with a compact JSON representation."""

    DEFAULTS = {
        "font_name": "Arial",
        "font_size": 10.0,
        "is_bold": False,
        "alignment": "left",
        "z_index": 0,
        "data_field": None,
        "fallback_text": "",
        "auto_scale": False,
        "visible": True,
    }

    def __init__(self, id_name: str, type_node: str, x: float, y: float,
                 w: float, h: float):
        self.id_name = id_name
        self.type_node = type_node
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)
        self.attributes: Dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        if key in self.DEFAULTS and self.DEFAULTS[key] == value:
            self.attributes.pop(key, None)
            return
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Any:
        return self.attributes.get(key, self.DEFAULTS.get(key))

    def to_compact_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id_name,
            "t": self.type_node,
            "g": [round(self.x, 2), round(self.y, 2), round(self.w, 2), round(self.h, 2)],
        }
        if self.attributes:
            data["a"] = self.attributes
        return data

    @classmethod
    def from_compact_dict(cls, data: Mapping[str, Any]) -> "OptimizedElement":
        coords = data.get("g", [0.0, 0.0, 0.0, 0.0])
        if len(coords) != 4:
            raise ValueError("element geometry must contain [x, y, w, h]")
        element = cls(
            id_name=data["id"],
            type_node=data.get("t", "Unknown"),
            x=coords[0], y=coords[1], w=coords[2], h=coords[3],
        )
        for key, value in data.get("a", {}).items():
            element.set_attribute(key, value)
        return element


class GraphicConstraint:
    """Structural anchor connecting two elements with a spring-like visual."""

    def __init__(self, id_name: str, source_id: str, source_edge: BoxEdge,
                 target_id: str, target_edge: BoxEdge,
                 min_distance: float = 5.0, max_distance: float = 30.0,
                 permanent_visibility: bool = True):
        self.id_name = id_name
        self.source_id = source_id
        self.source_edge = source_edge
        self.target_id = target_id
        self.target_edge = target_edge
        self.min_distance = float(min_distance)
        self.max_distance = float(max_distance)
        self.permanent_visibility = bool(permanent_visibility)
        self.is_hovered = False
        self._is_dirty = True
        self._cached_points_mm: List[Tuple[float, float]] = []
        self._cached_qpoints: List[QPointF] = []
        self._last_state_color = QColor(0, 120, 215)

    def invalider_cache(self) -> None:
        self._is_dirty = True
        self._cached_qpoints.clear()

    def _edge_point(self, element: OptimizedElement, edge: BoxEdge) -> Tuple[float, float]:
        if edge == BoxEdge.LEFT:
            return element.x, element.y + element.h / 2.0
        if edge == BoxEdge.RIGHT:
            return element.x + element.w, element.y + element.h / 2.0
        if edge == BoxEdge.TOP:
            return element.x + element.w / 2.0, element.y
        if edge == BoxEdge.BOTTOM:
            return element.x + element.w / 2.0, element.y + element.h
        if edge in (BoxEdge.CENTER_H, BoxEdge.CENTER_V):
            return element.x + element.w / 2.0, element.y + element.h / 2.0
        return element.x, element.y

    def _update_geometry_if_needed(self, elements: Mapping[str, OptimizedElement]) -> None:
        if not self._is_dirty:
            return
        if self.source_id not in elements or self.target_id not in elements:
            return

        src = elements[self.source_id]
        tgt = elements[self.target_id]
        x1, y1 = self._edge_point(src, self.source_edge)
        x2, y2 = self._edge_point(tgt, self.target_edge)
        dx, dy = x2 - x1, y2 - y1
        distance = math.hypot(dx, dy)

        if distance <= self.min_distance:
            self._last_state_color = QColor(230, 0, 0, 220)
        elif distance >= self.max_distance:
            self._last_state_color = QColor(255, 140, 0, 220)
        else:
            self._last_state_color = QColor(0, 200, 80, 180)
        if self.is_hovered:
            self._last_state_color = self._last_state_color.lighter(130)

        points: List[Tuple[float, float]] = [(x1, y1)]
        if distance > 0.0:
            nx, ny = -dy / distance, dx / distance
            x_start, y_start = x1 + dx * 0.15, y1 + dy * 0.15
            x_end, y_end = x1 + dx * 0.85, y1 + dy * 0.85
            points.append((x_start, y_start))

            nb_spires = 6
            total_segments = nb_spires * 2
            for i in range(1, total_segments):
                ratio = i / total_segments
                xb = x_start + (x_end - x_start) * ratio
                yb = y_start + (y_end - y_start) * ratio
                direction = 1 if i % 2 == 0 else -1
                points.append((xb + nx * 2.5 * direction, yb + ny * 2.5 * direction))
            points.append((x_end, y_end))
        points.append((x2, y2))
        self._cached_points_mm = points
        self._cached_qpoints.clear()
        self._is_dirty = False

    def evaluate_mouse_hover(self, mouse_x_mm: float, mouse_y_mm: float,
                             tolerance_mm: float = 2.0) -> bool:
        if not self._cached_points_mm:
            return False
        x1, y1 = self._cached_points_mm[0]
        x2, y2 = self._cached_points_mm[-1]
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy
        if length_sq == 0.0:
            return False

        projection = ((mouse_x_mm - x1) * dx + (mouse_y_mm - y1) * dy) / length_sq
        projection = max(0.0, min(1.0, projection))
        proj_x = x1 + projection * dx
        proj_y = y1 + projection * dy
        distance = math.hypot(mouse_x_mm - proj_x, mouse_y_mm - proj_y)

        previous = self.is_hovered
        self.is_hovered = distance <= tolerance_mm
        if previous != self.is_hovered:
            self.invalider_cache()
        return self.is_hovered

    def render(self, painter: QPainter, elements: Mapping[str, OptimizedElement],
               mm_to_pt: float) -> None:
        if not self.permanent_visibility and not self.is_hovered:
            return
        self._update_geometry_if_needed(elements)
        if not self._cached_points_mm:
            return

        painter.save()
        pen_width = 0.8 if self.is_hovered else 0.4
        painter.setPen(QPen(self._last_state_color, pen_width * mm_to_pt, Qt.SolidLine))

        if not self._cached_qpoints:
            for index in range(len(self._cached_points_mm) - 1):
                current = self._cached_points_mm[index]
                nxt = self._cached_points_mm[index + 1]
                self._cached_qpoints.append(QPointF(current[0] * mm_to_pt, current[1] * mm_to_pt))
                self._cached_qpoints.append(QPointF(nxt[0] * mm_to_pt, nxt[1] * mm_to_pt))

        painter.drawLines(self._cached_qpoints)
        painter.restore()

    def to_compact_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id_name,
            "src": [self.source_id, self.source_edge.value],
            "tgt": [self.target_id, self.target_edge.value],
            "lim": [round(self.min_distance, 1), round(self.max_distance, 1)],
            "vis": 1 if self.permanent_visibility else 0,
        }

    @classmethod
    def from_compact_dict(cls, data: Mapping[str, Any]) -> "GraphicConstraint":
        source = data.get("src", [None, BoxEdge.LEFT.value])
        target = data.get("tgt", [None, BoxEdge.RIGHT.value])
        limits = data.get("lim", [5.0, 30.0])
        if len(limits) != 2:
            limits = [5.0, 30.0]
        return cls(
            id_name=data.get("id", "constraint"),
            source_id=str(source[0]),
            source_edge=BoxEdge(source[1]),
            target_id=str(target[0]),
            target_edge=BoxEdge(target[1]),
            min_distance=float(limits[0]),
            max_distance=float(limits[1]),
            permanent_visibility=bool(data.get("vis", 1)),
        )


class ConstraintSolver:
    """Applies the spring constraints while respecting the label box."""

    @staticmethod
    def apply_constraints(el: OptimizedElement,
                          all_elements: Mapping[str, OptimizedElement],
                          constraints: Sequence[GraphicConstraint],
                          label_w: float, label_h: float) -> Tuple[float, float]:
        new_x, new_y = float(el.x), float(el.y)

        for constraint in constraints:
            if constraint.source_id != el.id_name and constraint.target_id != el.id_name:
                continue
            other_id = constraint.target_id if constraint.source_id == el.id_name else constraint.source_id
            other = all_elements.get(other_id)
            if other is None:
                continue
            moving_edge = constraint.source_edge if constraint.source_id == el.id_name else constraint.target_edge
            fixed_edge = constraint.target_edge if constraint.source_id == el.id_name else constraint.source_edge

            if fixed_edge == BoxEdge.LEFT:
                fixed_value = other.x
            elif fixed_edge == BoxEdge.RIGHT:
                fixed_value = other.x + other.w
            elif fixed_edge == BoxEdge.TOP:
                fixed_value = other.y
            elif fixed_edge == BoxEdge.BOTTOM:
                fixed_value = other.y + other.h
            else:
                continue

            if moving_edge == BoxEdge.LEFT:
                dist = new_x - fixed_value
                if abs(dist) < constraint.min_distance:
                    new_x = fixed_value + (constraint.min_distance if dist >= 0 else -constraint.min_distance)
            elif moving_edge == BoxEdge.RIGHT:
                dist = (new_x + el.w) - fixed_value
                if abs(dist) < constraint.min_distance:
                    new_x = fixed_value + (constraint.min_distance if dist >= 0 else -constraint.min_distance) - el.w
            elif moving_edge == BoxEdge.TOP:
                dist = new_y - fixed_value
                if abs(dist) < constraint.min_distance:
                    new_y = fixed_value + (constraint.min_distance if dist >= 0 else -constraint.min_distance)
            elif moving_edge == BoxEdge.BOTTOM:
                dist = (new_y + el.h) - fixed_value
                if abs(dist) < constraint.min_distance:
                    new_y = fixed_value + (constraint.min_distance if dist >= 0 else -constraint.min_distance) - el.h

        if new_x < 0:
            new_x = 0.0
        if new_x + el.w > label_w:
            new_x = max(0.0, label_w - el.w)
        if new_y < 0:
            new_y = 0.0
        if new_y + el.h > label_h:
            new_y = max(0.0, label_h - el.h)
        return new_x, new_y


class DataBindingResolver:
    """Resolves a dotted field path against a JSON-like data tree."""

    @staticmethod
    def resolve(expression: Optional[str], context_dict: Mapping[str, Any], fallback: str) -> str:
        if not expression:
            return str(fallback)
        current: Any = context_dict
        for part in str(expression).split("."):
            if not part:
                continue
            if isinstance(current, Mapping):
                if part not in current:
                    return str(fallback)
                current = current[part]
                continue
            if hasattr(current, part):
                current = getattr(current, part)
                continue
            return str(fallback)
        return "" if current is None else str(current)


class FontAutoScaler:
    """Reduces font size until the text fits the target box."""

    @staticmethod
    def optimize_font_size(text: str, font_name: str, max_w_pt: float, max_h_pt: float,
                           start_size: float, is_bold: bool) -> QFont:
        if not text:
            return QFont(font_name, start_size)
        current_size = max(4.0, float(start_size))
        font = QFont(font_name, current_size)
        font.setBold(bool(is_bold))

        while current_size > 4.0:
            metrics = QFontMetricsF(font)
            rect = metrics.boundingRect(text)
            if rect.width() <= max_w_pt and rect.height() <= max_h_pt:
                return font
            current_size -= 0.5
            font.setPointSizeF(current_size)
        return font


class MultiTemplateImpositionEngine:
    """Greedy placement of mixed template sizes on a page."""

    def __init__(self, page_w_mm: float = 210.0, page_h_mm: float = 297.0,
                 marge_mm: float = 6.0):
        self.page_w = float(page_w_mm)
        self.page_h = float(page_h_mm)
        self.marge = float(marge_mm)

    def arrange_mixed_templates(self, list_templates: Sequence[Tuple[float, float, Any]],
                                gap_x: float = 2.0, gap_y: float = 2.0) -> List[Tuple[float, float, Any]]:
        sorted_templates = sorted(list_templates, key=lambda item: (item[0] * item[1]), reverse=True)
        placements: List[Tuple[float, float, Any]] = []
        current_x = self.marge
        current_y = self.marge
        max_row_h = 0.0

        for width, height, payload in sorted_templates:
            width = float(width)
            height = float(height)
            if current_x + width > self.page_w - self.marge:
                current_x = self.marge
                current_y += max_row_h + gap_y
                max_row_h = 0.0
            if current_y + height > self.page_h - self.marge:
                continue
            placements.append((current_x, current_y, payload))
            max_row_h = max(max_row_h, height)
            current_x += width + gap_x
        return placements

    def arrange_mixed_templates_with_metadata(self, list_templates: Sequence[Tuple[float, float, Any]],
                                             gap_x: float = 2.0, gap_y: float = 2.0) -> List[Tuple[float, float, Any]]:
        return self.arrange_mixed_templates(list_templates, gap_x=gap_x, gap_y=gap_y)


class PrefabLabelTemplate:
    """Global template containing elements, constraints and JSON serialization."""

    def __init__(self, template_id: str, width_mm: float, height_mm: float):
        self.template_id = template_id
        self.width_mm = float(width_mm)
        self.height_mm = float(height_mm)
        self.elements: Dict[str, OptimizedElement] = {}
        self.constraints: List[GraphicConstraint] = []

    def add_element(self, element: OptimizedElement) -> OptimizedElement:
        self.elements[element.id_name] = element
        self.move_element(element.id_name, element.x, element.y)
        return element

    def add_constraint(self, constraint: GraphicConstraint) -> GraphicConstraint:
        self.constraints.append(constraint)
        constraint.invalider_cache()
        return constraint

    def move_element(self, id_name: str, tx: float, ty: float) -> OptimizedElement:
        if id_name not in self.elements:
            raise KeyError(f"unknown element: {id_name}")
        element = self.elements[id_name]
        element.x, element.y = float(tx), float(ty)
        new_x, new_y = ConstraintSolver.apply_constraints(
            element, self.elements, self.constraints, self.width_mm, self.height_mm
        )
        element.x, element.y = new_x, new_y
        for constraint in self.constraints:
            if constraint.source_id == id_name or constraint.target_id == id_name:
                constraint.invalider_cache()
        return element

    def to_compact_json(self) -> str:
        payload = {
            "id": self.template_id,
            "size": [self.width_mm, self.height_mm],
            "nodes": [item.to_compact_dict() for item in self.elements.values()],
            "springs": [constraint.to_compact_dict() for constraint in self.constraints],
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_compact_json(cls, payload: str) -> "PrefabLabelTemplate":
        return LayoutDeserializer.rebuild_template(payload)


class LayoutDeserializer:
    """Reverse deserialization to rebuild a template from compact JSON."""

    @staticmethod
    def rebuild_template(json_payload: str | Mapping[str, Any]) -> PrefabLabelTemplate:
        if isinstance(json_payload, str):
            data = json.loads(json_payload)
        else:
            data = dict(json_payload)

        size = data.get("size", [0.0, 0.0])
        if len(size) != 2:
            size = [0.0, 0.0]
        template = PrefabLabelTemplate(
            template_id=data.get("id", "template"),
            width_mm=float(size[0]),
            height_mm=float(size[1]),
        )

        for raw_node in data.get("nodes", []):
            element = OptimizedElement.from_compact_dict(raw_node)
            template.elements[element.id_name] = element

        for raw_spring in data.get("springs", []):
            constraint = GraphicConstraint.from_compact_dict(raw_spring)
            template.constraints.append(constraint)

        for constraint in template.constraints:
            constraint.invalider_cache()
        return template


class ProductionPipeline:
    """Renders a single element from a template using real data injection."""

    @staticmethod
    def execute_element(painter: QPainter, element: OptimizedElement,
                        context_data: Mapping[str, Any], mm_to_pt: float) -> None:
        painter.save()

        data_field = element.get_attribute("data_field")
        fallback = element.get_attribute("fallback_text")
        text = DataBindingResolver.resolve(data_field, context_data, fallback)

        font_name = element.get_attribute("font_name")
        font_size = float(element.get_attribute("font_size"))
        is_bold = bool(element.get_attribute("is_bold"))
        auto_scale = bool(element.get_attribute("auto_scale"))
        align_value = element.get_attribute("alignment")

        rect_target = QRectF(
            element.x * mm_to_pt,
            element.y * mm_to_pt,
            element.w * mm_to_pt,
            element.h * mm_to_pt,
        )

        if auto_scale and text:
            font = FontAutoScaler.optimize_font_size(
                text,
                font_name,
                element.w * mm_to_pt,
                element.h * mm_to_pt,
                font_size,
                is_bold,
            )
        else:
            font = QFont(font_name, font_size)
            font.setBold(is_bold)

        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))

        alignment = Qt.AlignLeft
        if align_value == "center":
            alignment = Qt.AlignCenter
        elif align_value == "right":
            alignment = Qt.AlignRight

        painter.drawText(rect_target, alignment | Qt.AlignVCenter | Qt.TextWordWrap, text)
        painter.restore()


__all__ = [
    "Alignment",
    "BoxEdge",
    "ConstraintSolver",
    "DataBindingResolver",
    "FontAutoScaler",
    "GraphicConstraint",
    "LayoutDeserializer",
    "MultiTemplateImpositionEngine",
    "OptimizedElement",
    "PrefabLabelTemplate",
    "ProductionPipeline",
]
