"""TextBox specialisees pour les champs d'une etiquette de prix."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

try:
    from .model import CharFormat, SizingMode
    from .textbox import TextBox
    from .label_design import (LabelFieldModel, PriceValue, ValidationResult)
except ImportError:  # pragma: no cover - support script execution
    from model import CharFormat, SizingMode
    from textbox import TextBox
    from label_design import LabelFieldModel, PriceValue, ValidationResult


class LabelField(TextBox):
    """Base des champs metier, avec un identifiant de role stable."""

    field_type = "text"

    def __init__(self, *args, field_id: str | None = None, **kwargs):
        self.required = kwargs.pop("required", False)
        self.max_length = kwargs.pop("max_length", None)
        self.max_lines = kwargs.pop("max_lines", None)
        self.pattern = kwargs.pop("pattern", None)
        super().__init__(*args, **kwargs)
        self.field_id = field_id or self.field_type
        self.setObjectName(self.field_id)

    def to_field_model(self) -> LabelFieldModel:
        return LabelFieldModel(field_type=self.field_type,
                               field_id=self.field_id,
                               value=self.text,
                               placeholder=self.model.placeholder,
                               required=self.required,
                               max_length=self.max_length,
                               max_lines=self.max_lines,
                               pattern=self.pattern)

    def validate(self) -> ValidationResult:
        return self.to_field_model().validate()


class Price(LabelField):
    field_type = "price"

    def __init__(self, value: Any = 0, currency: str = "€",
                 decimals: int = 2, decimal_separator: str = ",",
                 thousands_separator: str = " ", **kwargs):
        self.currency = currency
        self.decimals = decimals
        self.decimal_separator = decimal_separator
        self.thousands_separator = thousands_separator
        if decimals < 0 or decimals > 6:
            raise ValueError("decimals must be between 0 and 6")
        kwargs.setdefault("default_format", CharFormat(font_size=32.0, bold=True))
        kwargs.setdefault("placeholder", "0,00")
        super().__init__(text=self.format_value(value), **kwargs)
        self.value = self._to_decimal(value)
        if not self.value.is_finite():
            raise ValueError("price value must be finite")

    def _to_decimal(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("price value must be numeric") from exc

    def validate(self) -> ValidationResult:
        result = super().validate()
        if not self.value.is_finite():
            result.add("numeric", "price value must be finite")
        if self.value < 0:
            result.add("negative", "negative prices are not allowed")
        if not self.currency.strip():
            result.add("currency", "currency cannot be empty")
        return result

    def to_field_model(self) -> PriceValue:
        return PriceValue(field_id=self.field_id, value=self.value,
                          currency_code=self.currency,
                          decimals=self.decimals,
                          placeholder=self.model.placeholder)

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
        kwargs.setdefault("max_length", 80)
        kwargs.setdefault("default_format", CharFormat(font_size=24.0, bold=True))
        kwargs.setdefault("placeholder", "Marque")
        super().__init__(text=name, **kwargs)


class Description(LabelField):
    field_type = "description"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("max_lines", 5)
        kwargs.setdefault("default_format", CharFormat(font_size=16.0))
        kwargs.setdefault("sizing", SizingMode.FREE_RESIZE)
        kwargs.setdefault("placeholder", "Description du produit")
        super().__init__(text=text, **kwargs)


class PartNo(LabelField):
    field_type = "part_no"

    def __init__(self, value: str = "", **kwargs):
        kwargs.setdefault("max_length", 32)
        kwargs.setdefault("pattern", r"[A-Za-z0-9][A-Za-z0-9._/-]*")
        kwargs.setdefault("default_format", CharFormat(font_family="DejaVu Sans Mono",
                                                        font_size=14.0))
        kwargs.setdefault("placeholder", "REF-0000")
        super().__init__(text=value, **kwargs)


class Currency(LabelField):
    field_type = "currency"

    def __init__(self, symbol: str = "€", **kwargs):
        if not symbol.strip():
            raise ValueError("currency symbol cannot be empty")
        kwargs.setdefault("default_format", CharFormat(font_size=18.0, bold=True))
        super().__init__(text=symbol, **kwargs)
        self.symbol = symbol


class Discount(LabelField):
    field_type = "discount"

    def __init__(self, value: Any = 0, decimals: int = 0, **kwargs):
        self.value = Decimal(str(value).replace(",", "."))
        self.decimals = decimals
        kwargs.setdefault("default_format", CharFormat(font_size=18.0, bold=True))
        super().__init__(text=self.format_value(), **kwargs)

    def format_value(self) -> str:
        return f"{self.value.quantize(Decimal(1).scaleb(-self.decimals), rounding=ROUND_HALF_UP):.{self.decimals}f}%"

    def set_value(self, value: Any) -> None:
        self.value = Decimal(str(value).replace(",", "."))
        self.set_text(self.format_value())


class Weight(LabelField):
    field_type = "weight"

    def __init__(self, value: Any = 0, unit: str = "kg", decimals: int = 3,
                 **kwargs):
        self.value = Decimal(str(value).replace(",", "."))
        self.unit = unit
        self.decimals = decimals
        kwargs.setdefault("default_format", CharFormat(font_size=16.0))
        super().__init__(text=self.format_value(), **kwargs)

    def format_value(self) -> str:
        return f"{self.value:.{self.decimals}f} {self.unit}".strip()


class UnitPrice(Price):
    field_type = "unit_price"

    def __init__(self, value: Any = 0, unit: str = "kg",
                 geometry_unit: str = "px", **kwargs):
        self.unit_label = unit
        super().__init__(value=value, unit=geometry_unit, **kwargs)
        self.set_text(f"{self.text} / {self.unit_label}")


class CommercialName(LabelField):
    field_type = "commercial_name"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("max_lines", 2)
        kwargs.setdefault("default_format", CharFormat(font_size=20.0, bold=True))
        super().__init__(text=text, **kwargs)


class LegalName(LabelField):
    field_type = "legal_name"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("max_lines", 3)
        kwargs.setdefault("default_format", CharFormat(font_size=12.0))
        super().__init__(text=text, **kwargs)


class Origin(LabelField):
    field_type = "origin"

    def __init__(self, country: str = "", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=12.0))
        super().__init__(text=country, **kwargs)


class Variety(LabelField):
    field_type = "variety"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=12.0))
        super().__init__(text=text, **kwargs)


class Ingredients(LabelField):
    field_type = "ingredients"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("max_lines", 8)
        kwargs.setdefault("default_format", CharFormat(font_size=10.0))
        super().__init__(text=text, **kwargs)


class SanitaryStamp(LabelField):
    field_type = "sanitary_stamp"

    def __init__(self, code: str = "", **kwargs):
        kwargs.setdefault("pattern", r"[A-Za-z0-9 ./-]+")
        kwargs.setdefault("default_format", CharFormat(font_size=10.0))
        super().__init__(text=code, **kwargs)


class LoyaltyAdvantage(LabelField):
    field_type = "loyalty_advantage"

    def __init__(self, text: str = "+20% Crédités", **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=14.0, bold=True))
        super().__init__(text=text, **kwargs)


class ShrinkflationNotice(LabelField):
    field_type = "shrinkflation_notice"

    def __init__(self, text: str = "", **kwargs):
        kwargs.setdefault("max_lines", 2)
        kwargs.setdefault("default_format", CharFormat(font_size=9.0, bold=True))
        super().__init__(text=text, **kwargs)


class OriginalPrice(Price):
    field_type = "original_price"

    def __init__(self, value: Any = 0, **kwargs):
        kwargs.setdefault("default_format", CharFormat(font_size=18.0,
                                                        strikethrough=True))
        super().__init__(value=value, **kwargs)


# Aliases declaratifs utiles dans des templates de labels.
PRICE = Price
BRAND = Brand
DESCRIPTION = Description
PARTNO = PartNo
CURRENCY = Currency
DISCOUNT = Discount
WEIGHT = Weight
UNITPRICE = UnitPrice
COMMERCIAL_NAME = CommercialName
LEGAL_NAME = LegalName
ORIGIN = Origin
VARIETY = Variety
INGREDIENTS = Ingredients
SANITARY_STAMP = SanitaryStamp
LOYALTY_ADVANTAGE = LoyaltyAdvantage
SHRINKFLATION_NOTICE = ShrinkflationNotice
ORIGINAL_PRICE = OriginalPrice
