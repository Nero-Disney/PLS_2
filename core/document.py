"""Compatibility wrapper for the document and label business model."""

from .label_document import LabelDocument
from .label_design import PriceLabel

__all__ = ["LabelDocument", "PriceLabel"]
