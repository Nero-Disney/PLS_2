"""ERP and print-queue metadata for labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

from .label_design import ValidationResult
from .label_printing import PrintStatus


@dataclass
class ERPMetadata:
    sku: str = ""
    department_code: str = ""
    location_code: str = ""
    supplier_code: str = ""
    effective_from: Optional[datetime] = None
    promo_until: Optional[datetime] = None
    print_status: PrintStatus = PrintStatus.TO_PRINT
    print_error: str = ""

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if self.effective_from and self.promo_until and self.effective_from >= self.promo_until:
            result.add("erp_date_range", "ERP validity dates are invalid")
        if self.print_status == PrintStatus.ERROR and not self.print_error:
            result.add("print_error_missing", "print error status requires a message")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "department_code": self.department_code,
            "location_code": self.location_code,
            "supplier_code": self.supplier_code,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "promo_until": self.promo_until.isoformat() if self.promo_until else None,
            "print_status": self.print_status.value,
            "print_error": self.print_error,
        }
