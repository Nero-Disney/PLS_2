"""Domain models for printable price-label designs.

This module intentionally has no Qt dependency. It can validate, serialize and
batch-generate label data before an editor widget is created.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import json
import re
from typing import Any, Mapping, Optional

try:
    from .units import Unit
except ImportError:  # pragma: no cover - support direct module execution
    from units import Unit


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Severity = Severity.ERROR


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == Severity.ERROR for issue in self.issues)

    @property
    def errors(self) -> list[str]:
        return [i.message for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[str]:
        return [i.message for i in self.issues if i.severity == Severity.WARNING]

    def add(self, code: str, message: str,
            severity: Severity = Severity.ERROR) -> None:
        self.issues.append(ValidationIssue(code, message, severity))


@dataclass(frozen=True)
class TextStyle:
    font_family: str = "Arial"
    font_size: float = 18.0
    bold: bool = False
    italic: bool = False
    color: str = "#000000"
    alignment: str = "left"


@dataclass
class LabelTheme:
    name: str = "default"
    styles: dict[str, TextStyle] = field(default_factory=dict)

    def style_for(self, field_type: str) -> TextStyle:
        return self.styles.get(field_type, TextStyle())

    def merged_style(self, field_type: str,
                     override: Optional[TextStyle] = None) -> TextStyle:
        base = self.style_for(field_type)
        if override is None:
            return base
        values = asdict(base)
        values.update({key: value for key, value in asdict(override).items()
                       if value is not None})
        return TextStyle(**values)


@dataclass
class LabelFieldModel:
    field_type: str = "text"
    field_id: str = "field"
    value: Any = ""
    label: str = ""
    required: bool = False
    visible: bool = True
    read_only: bool = False
    placeholder: str = ""
    max_length: Optional[int] = None
    max_lines: Optional[int] = None
    pattern: Optional[str] = None
    style_name: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    locked: bool = False

    def display_value(self) -> str:
        return "" if self.value is None else str(self.value)

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        display = self.display_value()
        if self.required and not display.strip():
            result.add("required", f"{self.field_id} is required")
        if self.max_length is not None and len(display) > self.max_length:
            result.add("max_length", f"{self.field_id} exceeds maximum length")
        if self.max_lines is not None and display.count("\n") + 1 > self.max_lines:
            result.add("max_lines", f"{self.field_id} exceeds maximum lines")
        if self.pattern and display and not re.fullmatch(self.pattern, display):
            result.add("pattern", f"{self.field_id} has an invalid format")
        if self.width < 0 or self.height < 0:
            result.add("geometry", f"{self.field_id} has invalid dimensions")
        return result

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.__class__.__name__
        return data


@dataclass
class PriceValue(LabelFieldModel):
    field_type: str = "price"
    currency_code: str = "EUR"
    locale: str = "fr-FR"
    decimals: int = 2
    rounding: str = "HALF_UP"
    allow_negative: bool = False
    symbol_position: str = "after"
    grouping: bool = True

    def _decimal(self) -> Decimal:
        try:
            value = Decimal(str(self.value).strip().replace(",", "."))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("price value must be numeric") from exc
        if not value.is_finite():
            raise ValueError("price value must be finite")
        return value

    def display_value(self) -> str:
        value = self._decimal().quantize(
            Decimal(1).scaleb(-self.decimals), rounding=ROUND_HALF_UP)
        negative = value < 0
        absolute = abs(value)
        raw = f"{absolute:,.{self.decimals}f}"
        if self.locale.lower().startswith(("fr", "de", "es", "it")):
            raw = raw.replace(",", "GROUP").replace(".", ",")
            raw = raw.replace("GROUP", "\u202f" if self.grouping else "")
            symbol = {"EUR": "€", "USD": "$", "GBP": "£"}.get(
                self.currency_code.upper(), self.currency_code)
            formatted = f"{raw} {symbol}" if self.symbol_position == "after" else f"{symbol}{raw}"
        else:
            symbol = {"EUR": "€", "USD": "$", "GBP": "£"}.get(
                self.currency_code.upper(), self.currency_code)
            if not self.grouping:
                raw = raw.replace(",", "")
            formatted = f"{symbol}{raw}" if self.symbol_position == "before" else f"{raw} {symbol}"
        return f"-{formatted}" if negative else formatted

    def validate(self) -> ValidationResult:
        result = super().validate()
        if self.decimals < 0 or self.decimals > 6:
            result.add("decimals", "decimal places must be between 0 and 6")
        if self.currency_code.upper() not in {"EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD"}:
            result.add("currency", "unsupported currency code", Severity.WARNING)
        try:
            value = self._decimal()
            if value < 0 and not self.allow_negative:
                result.add("negative", "negative prices are not allowed")
        except ValueError as exc:
            result.add("numeric", str(exc))
        return result


@dataclass
class BarcodeModel(LabelFieldModel):
    field_type: str = "barcode"
    symbology: str = "CODE128"
    quiet_zone_mm: float = 2.0
    human_readable: bool = True

    def validate(self) -> ValidationResult:
        result = super().validate()
        if not self.display_value():
            result.add("payload", "barcode payload is empty")
        if self.quiet_zone_mm < 2.0:
            result.add("quiet_zone", "barcode quiet zone is below 2 mm", Severity.WARNING)
        if self.symbology.upper() not in {"CODE128", "EAN13", "UPC_A", "QR"}:
            result.add("symbology", "unsupported barcode symbology")
        return result


@dataclass
class LabelDocument:
    width: float
    height: float
    unit: Unit = Unit.MILLIMETER
    dpi: float = 300.0
    fields: list[LabelFieldModel] = field(default_factory=list)
    theme: LabelTheme = field(default_factory=LabelTheme)
    product: Any = None
    price_data: Any = None
    promotion: Any = None
    graphics: list[Any] = field(default_factory=list)
    print_spec: Any = None
    system_data: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def add(self, field_model: LabelFieldModel) -> LabelFieldModel:
        if any(item.field_id == field_model.field_id for item in self.fields):
            raise ValueError(f"duplicate field id: {field_model.field_id}")
        self.fields.append(field_model)
        return field_model

    def add_graphic(self, graphic: Any) -> Any:
        self.graphics.append(graphic)
        return graphic

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if self.width <= 0 or self.height <= 0:
            result.add("dimensions", "label dimensions must be positive")
        if self.dpi <= 0:
            result.add("dpi", "label DPI must be positive")
        for field_model in self.fields:
            result.issues.extend(field_model.validate().issues)
            if (field_model.x < 0 or field_model.y < 0 or
                    field_model.x + field_model.width > self.width or
                    field_model.y + field_model.height > self.height):
                result.add("out_of_bounds",
                           f"{field_model.field_id} is outside the label bounds")
        for component in (self.product, self.price_data, self.promotion,
                          self.print_spec):
            if component is not None and hasattr(component, "validate"):
                result.issues.extend(component.validate().issues)
        for graphic in self.graphics:
            result.issues.extend(graphic.validate().issues)
        for index, first in enumerate(self.fields):
            for second in self.fields[index + 1:]:
                if self._overlaps(first, second):
                    result.add("overlap",
                               f"{first.field_id} overlaps {second.field_id}",
                               Severity.WARNING)
        return result

    @staticmethod
    def _overlaps(first: LabelFieldModel, second: LabelFieldModel) -> bool:
        if first.width <= 0 or first.height <= 0 or second.width <= 0 or second.height <= 0:
            return False
        return (first.x < second.x + second.width and
                first.x + first.width > second.x and
                first.y < second.y + second.height and
                first.y + first.height > second.y)

    def to_dict(self) -> dict[str, Any]:
        def serialize(value: Any) -> Any:
            if value is None:
                return None
            if hasattr(value, "to_dict"):
                return value.to_dict()
            if hasattr(value, "isoformat"):
                return value.isoformat()
            if isinstance(value, Enum):
                return value.value
            return value

        return {
            "schema_version": self.schema_version,
            "width": self.width,
            "height": self.height,
            "unit": self.unit.value,
            "dpi": self.dpi,
            "theme": {"name": self.theme.name,
                      "styles": {key: asdict(value) for key, value in self.theme.styles.items()}},
            "fields": [item.to_dict() for item in self.fields],
            "product": serialize(self.product),
            "price_data": serialize(self.price_data),
            "promotion": serialize(self.promotion),
            "graphics": [serialize(item) for item in self.graphics],
            "print_spec": serialize(self.print_spec),
            "system_data": self.system_data,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LabelDocument":
        version = int(data.get("schema_version", 1))
        if version != 1:
            raise ValueError(f"unsupported label schema version: {version}")
        document = cls(float(data["width"]), float(data["height"]),
                       Unit(data.get("unit", Unit.MILLIMETER.value)),
                       float(data.get("dpi", 300.0)))
        theme_data = data.get("theme", {})
        document.theme = LabelTheme(
            name=theme_data.get("name", "default"),
            styles={key: TextStyle(**value)
                    for key, value in theme_data.get("styles", {}).items()},
        )
        if data.get("product"):
            from .label_product import ProductData
            product_data = dict(data["product"])
            if product_data.get("net_quantity") is not None:
                from decimal import Decimal
                product_data["net_quantity"] = Decimal(product_data["net_quantity"])
            document.product = ProductData(**product_data)
        if data.get("price_data"):
            from .label_product import PriceData
            from decimal import Decimal
            price_data = dict(data["price_data"])
            for key in ("sale_price", "original_price", "loyalty_percent"):
                if price_data.get(key) is not None:
                    price_data[key] = Decimal(price_data[key])
            document.price_data = PriceData(**price_data)
        if data.get("promotion"):
            from .label_product import PromotionData
            document.promotion = PromotionData(**dict(data["promotion"]))
        if data.get("print_spec"):
            from .label_printing import PrintSpec, ColorMode, Orientation, PrintStatus, PrintSupport
            spec = dict(data["print_spec"])
            spec["support"] = PrintSupport(spec.get("support", PrintSupport.THERMAL))
            spec["orientation"] = Orientation(spec.get("orientation", Orientation.PORTRAIT))
            spec["color_mode"] = ColorMode(spec.get("color_mode", ColorMode.MONOCHROME))
            spec["status"] = PrintStatus(spec.get("status", PrintStatus.TO_PRINT))
            document.print_spec = PrintSpec(**spec)
        if data.get("system_data"):
            document.system_data = dict(data["system_data"])
        for raw in data.get("fields", []):
            field_data = dict(raw)
            kind = field_data.pop("kind", "LabelFieldModel")
            field_class = {"PriceValue": PriceValue,
                           "BarcodeModel": BarcodeModel}.get(kind,
                                                               LabelFieldModel)
            document.add(field_class(**field_data))
        return document

    @classmethod
    def from_json(cls, value: str) -> "LabelDocument":
        return cls.from_dict(json.loads(value))


PriceField = PriceValue
BarcodeField = BarcodeModel
PriceLabel = LabelDocument