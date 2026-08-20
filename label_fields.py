"""TextBox specialisees pour les champs d'une etiquette de prix."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

try:
    from .model import CharFormat, SizingMode
    from .textbox import TextBox
except ImportError:  # pragma: no cover - support script execution
    from model import CharFormat, SizingMode
    from textbox import TextBox


class LabelField(TextBox):
    """Base des champs metier, avec un identifiant de role stable."""

    field_type = "text"

    def __init__(self, *args, field_id: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_id = field_id or self.field_type
        self.setObjectName(self.field_id)


class Price(LabelField):
    field_type = "price"

    def __init__(self, value: Any = 0, currency: str = "€",
                 decimals: int = 2, decimal_separator: str = ",",
                 thousands_separator: str = " ", **kwargs):
        self.currency = currency
        self.decimals = decimals
        self.decimal_separator = decimal_separator
        self.thousands_separator = thousands_separator
        kwargs.setdefault("default_format", CharFormat(font_size=32.0, bold=True))
        kwargs.setdefault("placeholder", "0,00")
        super().__init__(text=self.format_value(value), **kwargs)
        self.value = self._to_decimal(value)

    def _to_decimal(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("price value must be numeric") from exc

    def format_value(self, value: Any) -> str:
        number = self._to_decimal(value).quantize(
            Decimal(1).scaleb(-self.decimals), rounding=ROUND_HALF_UP)
        raw = f"{number:,.{self.decimals}f}"
        raw = raw.replace(",", "GROUP").replace(".", self.decimal_separator)
        raw = raw.replace("GROUP", self.thousands_separator)
        return f"{raw} {self.currency}".strip()

    def set_value(self, value: Any) -> None:
        self.value = self._to_decimal(value)
        self.set_text(self.format_value(self.value))


class Brand(LabelField):
    field_type = "brand"

    def __init__(self, name: str = "", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=24.0, bold=True))
        kwargs.setdefault("placeholder", "Marque")
        super().__init__(text=name, **kwargs)


class Description(LabelField):
    field_type = "description"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=16.0))
        kwargs.setdefault("sizing", SizingMode.FREE_RESIZE)
        kwargs.setdefault("placeholder", "Description du produit")
        super().__init__(text=text, **kwargs)


class PartNo(LabelField):
    field_type = "part_no"

    def __init__(self, value: str = "", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_family="DejaVu Sans Mono",
                                                        font_size=14.0))
        kwargs.setdefault("placeholder", "REF-0000")
        super().__init__(text=value, **kwargs)


class Currency(LabelField):
    field_type = "currency"

    def __init__(self, symbol: str = "€", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=18.0, bold=True))
        super().__init__(text=symbol, **kwargs)
        self.symbol = symbol


# Aliases declaratifs utiles dans des templates de labels.
PRICE = Price
BRAND = Brand
DESCRIPTION = Description
PARTNO = PartNo
CURRENCY = Currency
