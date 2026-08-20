"""Conversions de dimensions pour l'editeur de documents et d'etiquettes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Unit(str, Enum):
    PIXEL = "px"
    MILLIMETER = "mm"
    POINT = "pt"


@dataclass(frozen=True)
class DocumentSpec:
    """Parametres physiques d'un document ou d'une cible d'impression."""

    dpi: float = 96.0
    unit: Unit = Unit.PIXEL

    def __post_init__(self):
        if self.dpi <= 0:
            raise ValueError("dpi must be greater than zero")


def to_pixels(value: float, unit: Unit | str, dpi: float = 96.0) -> float:
    """Convertir une dimension de document en pixels de rendu."""
    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")
    unit = Unit(unit)
    if unit == Unit.PIXEL:
        return float(value)
    if unit == Unit.MILLIMETER:
        return float(value) * dpi / 25.4
    return float(value) * dpi / 72.0


def from_pixels(value: float, unit: Unit | str, dpi: float = 96.0) -> float:
    """Convertir une dimension de rendu en unite de document."""
    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")
    unit = Unit(unit)
    if unit == Unit.PIXEL:
        return float(value)
    if unit == Unit.MILLIMETER:
        return float(value) * 25.4 / dpi
    return float(value) * 72.0 / dpi


def convert(value: float, source: Unit | str, target: Unit | str,
            dpi: float = 96.0) -> float:
    """Convertir une dimension entre deux unites via les pixels."""
    return from_pixels(to_pixels(value, source, dpi), target, dpi)
