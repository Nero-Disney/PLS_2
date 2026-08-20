"""Template and prefab engine, isolated as a dedicated module.

This module keeps the label-template orchestration separate from the document
business model and the Qt editor widgets. It exposes the compact serialization,
constraint solving, data binding and mixed-template placement logic used by the
print-ready label engine.
"""

from .label_engine import (
    Alignment,
    BoxEdge,
    ConstraintSolver,
    DataBindingResolver,
    FontAutoScaler,
    GraphicConstraint,
    LayoutDeserializer,
    MultiTemplateImpositionEngine,
    OptimizedElement,
    PrefabLabelTemplate,
    ProductionPipeline,
)

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
