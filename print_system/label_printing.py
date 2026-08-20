"""Label template and print-production settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..core.label_design import ValidationResult
from ..editor.units import Unit


class Orientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PrintSupport(str, Enum):
    THERMAL = "thermal"
    LASER_SHEET = "laser_sheet"
    CARD = "card"


class ColorMode(str, Enum):
    MONOCHROME = "monochrome"
    BLACK_RED = "black_red"
    CMYK = "cmyk"


class PrintStatus(str, Enum):
    TO_PRINT = "to_print"
    PRINTED = "printed"
    ERROR = "error"


@dataclass
class PrintSpec:
    template_id: str = "default"
    support: PrintSupport = PrintSupport.THERMAL
    orientation: Orientation = Orientation.PORTRAIT
    color_mode: ColorMode = ColorMode.MONOCHROME
    dpi: float = 300.0
    bleed: float = 0.0
    safe_margin: float = 2.0
    copies: int = 1
    status: PrintStatus = PrintStatus.TO_PRINT
    sort_key: str = "sku"
    sheet_columns: int = 1
    sheet_rows: int = 1

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if self.dpi <= 0:
            result.add("print_dpi", "print DPI must be positive")
        if self.copies < 1:
            result.add("copies", "copies must be at least one")
        if self.safe_margin < 0 or self.bleed < 0:
            result.add("margins", "bleed and safe margin cannot be negative")
        if self.sheet_columns < 1 or self.sheet_rows < 1:
            result.add("sheet_grid", "sheet rows and columns must be positive")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "support": self.support.value,
            "orientation": self.orientation.value,
            "color_mode": self.color_mode.value,
            "dpi": self.dpi,
            "bleed": self.bleed,
            "safe_margin": self.safe_margin,
            "copies": self.copies,
            "status": self.status.value,
            "sort_key": self.sort_key,
            "sheet_columns": self.sheet_columns,
            "sheet_rows": self.sheet_rows,
        }
