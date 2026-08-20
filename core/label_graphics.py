"""Graphic assets and pictograms placed on a label."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .label_design import LabelFieldModel, Severity, ValidationResult


class GraphicKind(str, Enum):
    LOGO = "logo"
    LABEL_ICON = "label_icon"
    NUTRI_SCORE = "nutri_score"
    ECO_SCORE = "eco_score"
    BACKGROUND = "background"
    QR_CODE = "qr_code"
    BARCODE = "barcode"
    IMAGE = "image"


@dataclass
class GraphicElement(LabelFieldModel):
    field_type: str = "graphic"
    asset_id: str = ""
    asset_path: str = ""
    graphic_kind: GraphicKind = GraphicKind.IMAGE
    payload: str = ""
    foreground: str = "#000000"
    background: str = "#ffffff"

    def validate(self) -> ValidationResult:
        result = super().validate()
        if not self.asset_id and not self.asset_path and not self.payload and not self.display_value():
            result.add("graphic_source", f"{self.field_id} has no asset or payload")
        if self.width <= 0 or self.height <= 0:
            result.add("graphic_size", f"{self.field_id} has invalid graphic size")
        return result

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["graphic_kind"] = self.graphic_kind.value
        return data


@dataclass
class BarcodeElement(GraphicElement):
    field_type: str = "barcode_element"
    graphic_kind: GraphicKind = GraphicKind.BARCODE
    symbology: str = "EAN13"
    quiet_zone_mm: float = 2.0
    error_correction: str = "M"

    def validate(self) -> ValidationResult:
        result = super().validate()
        if self.symbology.upper() not in {"EAN13", "EAN8", "CODE128", "CODE39", "QR", "DATAMATRIX"}:
            result.add("symbology", "unsupported barcode symbology")
        if self.quiet_zone_mm < 2:
            result.add("quiet_zone", "quiet zone is below 2 mm", Severity.WARNING)
        return result


@dataclass
class LogoElement(GraphicElement):
    field_type: str = "logo"
    graphic_kind: GraphicKind = GraphicKind.LOGO


@dataclass
class PictogramElement(GraphicElement):
    field_type: str = "pictogram"
    graphic_kind: GraphicKind = GraphicKind.LABEL_ICON
