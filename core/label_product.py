"""Product and pricing data used to populate labels."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

try:
    from .label_design import ValidationResult
except ImportError:  # pragma: no cover
    from label_design import ValidationResult


@dataclass
class ProductData:
    sku: str = ""
    commercial_name: str = ""
    legal_name: str = ""
    brand: str = ""
    origin: str = ""
    variety: str = ""
    calibre: str = ""
    category: str = ""
    department_code: str = ""
    location_code: str = ""
    ingredients: str = ""
    allergens: str = ""
    sanitary_stamp: str = ""
    net_quantity: Optional[Decimal] = None
    reference_unit: str = "piece"
    net_unit: str = ""
    shrinkflation_notice: str = ""

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if not self.sku.strip():
            result.add("sku_missing", "product SKU is empty")
        if self.net_quantity is not None:
            if not self.net_quantity.is_finite() or self.net_quantity <= 0:
                result.add("quantity_invalid", "net quantity must be positive and finite")
        if not self.reference_unit.strip():
            result.add("reference_unit_missing", "reference unit is empty")
        return result

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.net_quantity is not None:
            data["net_quantity"] = str(self.net_quantity)
        return data


@dataclass
class PriceData:
    sale_price: Decimal = Decimal("0")
    currency_code: str = "EUR"
    original_price: Optional[Decimal] = None
    loyalty_percent: Optional[Decimal] = None
    tax_included: bool = True
    effective_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    def unit_price(self, quantity: Optional[Decimal], reference_unit: str) -> Optional[Decimal]:
        if quantity is None or quantity <= 0:
            return None
        return (self.sale_price / quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        for name, value in (("sale_price", self.sale_price),
                            ("original_price", self.original_price),
                            ("loyalty_percent", self.loyalty_percent)):
            if value is not None and not value.is_finite():
                result.add(f"{name}_invalid", f"{name} must be finite")
        if self.sale_price < 0:
            result.add("sale_price_negative", "sale price cannot be negative")
        if self.original_price is not None and self.original_price < 0:
            result.add("original_price_negative", "original price cannot be negative")
        if self.loyalty_percent is not None and not (0 <= self.loyalty_percent <= 100):
            result.add("loyalty_percent_invalid", "loyalty percent must be between 0 and 100")
        if self.effective_from and self.valid_until and self.effective_from >= self.valid_until:
            result.add("date_range_invalid", "price effective dates are invalid")
        return result

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("sale_price", "original_price", "loyalty_percent"):
            if data[key] is not None:
                data[key] = str(data[key])
        for key in ("effective_from", "valid_until"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data


@dataclass
class PromotionData:
    advantage_text: str = ""
    discount_percent: Optional[Decimal] = None
    shrinkflation_notice: str = ""
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if self.discount_percent is not None and not (0 <= self.discount_percent <= 100):
            result.add("discount_invalid", "discount must be between 0 and 100")
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            result.add("promotion_dates_invalid", "promotion dates are invalid")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "advantage_text": self.advantage_text,
            "discount_percent": str(self.discount_percent)
            if self.discount_percent is not None else None,
            "shrinkflation_notice": self.shrinkflation_notice,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
        }


def decimal_value(value: Any) -> Decimal:
    try:
        result = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("value must be numeric") from exc
    if not result.is_finite():
        raise ValueError("value must be finite")
    return result
