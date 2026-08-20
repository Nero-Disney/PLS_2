import importlib
import os
import sys
from pathlib import Path

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from PLS_2 import (BoxEdge, DataBindingResolver, GraphicConstraint,
                   LayoutDeserializer, MultiTemplateImpositionEngine,
                   OptimizedElement, PrefabLabelTemplate)
from PLS_2.editor.cursor import Position, TextCursor
from PLS_2.editor.layout_engine import LayoutEngine
from PLS_2.editor.model import (Overflow, SizingMode, TextObject, VAlign, Paragraph,
                               CharFormat)
from PLS_2.editor.view import TextObjectView


app = QApplication.instance() or QApplication([])


def test_vertical_offset_respects_autofit_shrink():
    obj = TextObject(QRectF(0, 0, 200, 200), paragraphs=[Paragraph("hello")])
    obj.valign = VAlign.MIDDLE
    obj.overflow = Overflow.AUTOFIT_SHRINK

    view = TextObjectView(obj)
    assert view._vertical_offset(view._layout_result, obj.content_rect()) == 0.0


def test_package_exports_public_api():
    pkg = importlib.import_module("PLS_2")

    assert hasattr(pkg, "TextObjectView")
    assert "TextObjectView" in getattr(pkg, "__all__", [])
    assert hasattr(pkg, "TextBox")
    assert "TextBox" in getattr(pkg, "__all__", [])


def test_bounding_box_has_eight_handles_and_respects_minimum_size():
    obj = TextObject(QRectF(0, 0, 200, 100), paragraphs=[Paragraph("hello")])
    view = TextObjectView(obj)

    handles = set(view._handle_rects())
    assert handles - {"rotate"} == {
        "top_left", "top", "top_right", "right",
        "bottom_right", "bottom", "bottom_left", "left",
    }
    assert "rotate" in handles

    view._drag_geometry = view.geometry()
    view._drag_handle = "top_left"
    view._resize_geometry(QPointF(500, 500), Qt.NoModifier)

    assert view.width() >= view.MIN_WIDTH
    assert view.height() >= view.MIN_HEIGHT


def test_rotation_handle_and_inverse_transform_are_available():
    obj = TextObject(QRectF(0, 0, 200, 100), paragraphs=[Paragraph("hello")])
    view = TextObjectView(obj)
    view.obj.rotation = 45.0

    assert view._handle_at(view._handle_rects()["rotate"].center()) == "rotate"
    local = QPointF(30, 20)
    transformed = view._view_point(local)
    restored = view._local_point(transformed)
    assert abs(restored.x() - local.x()) < 0.001
    assert abs(restored.y() - local.y()) < 0.001


def test_autofit_grow_expands_the_model_box():
    obj = TextObject(QRectF(0, 0, 100, 20), paragraphs=[Paragraph("long text " * 20)])
    obj.overflow = Overflow.AUTOFIT_GROW
    result = LayoutEngine().layout(obj)

    assert result.total_height > 0
    assert obj.box.height() >= result.total_height + obj.margins[2] + obj.margins[3]


def test_cursor_preserves_character_format_and_supports_undo_redo():
    paragraph = Paragraph("bold", default_format=CharFormat(bold=True))
    cursor = TextCursor(TextObject(QRectF(0, 0, 200, 100), [paragraph]))
    cursor.position = Position(0, 4)
    cursor.insert_paragraph_break()
    cursor.insert_text("x")

    assert cursor.obj.paragraphs[1].format_at(0).bold
    assert cursor.undo()
    assert cursor.obj.paragraphs[1].text == ""
    assert cursor.redo()
    assert cursor.obj.paragraphs[1].text == "x"


def test_selection_paints_without_qt_cursor_coordinate_errors():
    obj = TextObject(QRectF(0, 0, 240, 120), paragraphs=[Paragraph("selection render")])
    view = TextObjectView(obj)
    view.cursor.set_selection(Position(0, 0), Position(0, 9))
    image = QImage(240, 120, QImage.Format_ARGB32)
    image.fill(0)

    view.render(image)

    assert not image.isNull()


def test_textbox_sizing_modes_and_placeholder():
    from PLS_2.editor.textbox import TextBox

    auto = TextBox(text="texte initial", width=420, height=220)
    assert auto.model.sizing_mode == SizingMode.AUTO_FIT_CONTENT
    assert auto.width() < 420

    placeholder = TextBox(placeholder="Votre titre", width=420, height=220)
    assert placeholder.width() >= 40
    assert placeholder.model.placeholder == "Votre titre"

    free = TextBox(text="free", sizing="free_resize", width=200, height=100)
    free.resize_box(300, 140)
    assert free.width() == 300

    locked = TextBox(text="locked", sizing="locked", width=200, height=100)
    locked.resize_box(300, 140)
    assert locked.width() == 200


def test_arrow_keys_collapse_selection_to_the_expected_edge():
    view = TextObjectView(TextObject(QRectF(0, 0, 200, 100),
                                     [Paragraph("abcdef")]))
    cursor = view.cursor
    cursor.set_selection(Position(0, 1), Position(0, 5))

    view._move(-1, extend=False)
    assert cursor.position == Position(0, 1)
    assert not cursor.has_selection()

    cursor.set_selection(Position(0, 1), Position(0, 5))
    view._move(1, extend=False)
    assert cursor.position == Position(0, 5)
    assert not cursor.has_selection()


def test_multiline_insert_creates_paragraphs():
    obj = TextObject(QRectF(0, 0, 200, 100), [Paragraph("beforeafter")])
    cursor = TextCursor(obj)
    cursor.position = Position(0, 6)

    cursor.insert_text("one\ntwo")

    assert [paragraph.text for paragraph in obj.paragraphs] == [
        "beforeone", "twoafter"
    ]
    assert cursor.position == Position(1, 3)


def test_format_read_is_not_an_undo_edit():
    obj = TextObject(QRectF(0, 0, 200, 100), [Paragraph("hello")])
    cursor = TextCursor(obj)
    cursor.set_selection(Position(0, 0), Position(0, 5))
    cursor.current_format()
    cursor.apply_format_to_selection_or_pending(bold=True)

    assert obj.paragraphs[0].format_at(0).bold
    assert cursor.undo()
    assert not obj.paragraphs[0].format_at(0).bold


def test_auto_fit_uses_character_format_metrics():
    from PLS_2.editor.textbox import TextBox
    large = Paragraph("Large", default_format=CharFormat(font_size=48.0))
    box = TextBox(paragraphs=[large], width=100, height=40)

    assert box.height() >= 50
    assert box.width() > 100


def test_physical_units_are_converted_with_explicit_dpi():
    from PLS_2.editor.textbox import TextBox
    from PLS_2.editor.units import Unit, from_pixels, to_pixels

    assert abs(to_pixels(25.4, Unit.MILLIMETER, 300) - 300.0) < 0.001
    assert abs(from_pixels(300, Unit.MILLIMETER, 300) - 25.4) < 0.001
    box = TextBox(text="Prix", x=10, y=5, width=50, height=20,
                  unit="mm", dpi=300, sizing="free_resize")
    assert abs(box.width() - to_pixels(50, "mm", 300)) <= 1
    assert abs(box.x() - to_pixels(10, "mm", 300)) <= 1


def test_label_field_subclasses_keep_textbox_behavior_and_domain_defaults():
    from PLS_2.fields.label_fields import BRAND, DESCRIPTION, PARTNO, PRICE

    brand = BRAND("Acme")
    price = PRICE("12,995", currency="EUR", decimals=2)
    description = DESCRIPTION("Produit")
    part_number = PARTNO("AC-2048")

    assert brand.text == "Acme"
    assert price.text == "13,00 EUR"
    assert price.field_id == "price"
    assert description.obj.sizing_mode == SizingMode.FREE_RESIZE
    assert part_number.text == "AC-2048"
    assert len(price._handle_rects()) == 9


def test_label_domain_supports_special_fields_and_json_round_trip():
    from PLS_2.core.label_design import BarcodeField, LabelDocument, PriceValue
    from PLS_2.fields.label_fields import Discount, UnitPrice, Weight

    assert PriceValue(field_id="price", value="12,995").display_value() == "13,00 €"
    assert Discount(20).text == "20%"
    assert Weight(1.25, unit="kg").text == "1.250 kg"
    assert "/ kg" in UnitPrice(3.5, unit="kg").text

    document = LabelDocument(80, 50)
    document.add(PriceValue(field_id="price", value="12.99"))
    document.add(BarcodeField(field_id="barcode", value="123456"))
    restored = LabelDocument.from_json(document.to_json())
    assert [item.field_id for item in restored.fields] == ["price", "barcode"]
    assert restored.validate().valid


def test_label_document_checks_bounds_and_overlaps():
    from PLS_2.core.label_design import LabelDocument, LabelFieldModel, Severity

    document = LabelDocument(80, 50)
    document.add(LabelFieldModel(field_id="brand", value="Acme",
                                 x=5, y=5, width=30, height=10))
    document.add(LabelFieldModel(field_id="price", value="10",
                                 x=20, y=8, width=30, height=10))
    result = document.validate()
    assert result.valid
    assert any(issue.code == "overlap" and
               issue.severity == Severity.WARNING for issue in result.issues)


def test_printing_service_exports_a_label_to_pdf(tmp_path):
    from PLS_2.core.label_design import LabelDocument, PriceValue
    from PLS_2.print_system.printing import LabelPrinter

    document = LabelDocument(50, 30)
    document.add(PriceValue(field_id="price", value="9.99",
                            x=5, y=5, width=20, height=10))
    output = tmp_path / "label.pdf"
    assert LabelPrinter(document).export_pdf(str(output)) == str(output)
    assert output.exists() and output.stat().st_size > 0


def test_label_architecture_modules_are_importable():
    from PLS_2.core.label_document import LabelDocument as DocumentModule
    from PLS_2.core.label_elements import PriceField as PriceModule
    from PLS_2.core.label_styles import LabelTheme as ThemeModule
    from PLS_2.core.label_validation import ValidationResult as ValidationModule

    assert DocumentModule is not None
    assert PriceModule is not None
    assert ThemeModule is not None
    assert ValidationModule is not None


def test_prefab_json_round_trip_and_databinding_are_supported():
    from PLS_2 import DataBindingResolver, GraphicConstraint, LayoutDeserializer, MultiTemplateImpositionEngine, OptimizedElement, PrefabLabelTemplate
    from PLS_2 import BoxEdge

    template = PrefabLabelTemplate("T-01", 105.0, 74.0)
    brand = OptimizedElement("brand_box", "Brand", 5.0, 5.0, 40.0, 10.0)
    brand.set_attribute("data_field", "erp.produit.marque")
    template.add_element(brand)

    title = OptimizedElement("title_box", "StaticText", 5.0, 18.0, 50.0, 12.0)
    title.set_attribute("fallback_text", "Produit")
    template.add_element(title)
    template.add_constraint(GraphicConstraint("c1", "brand_box", BoxEdge.BOTTOM,
                                             "title_box", BoxEdge.TOP,
                                             min_distance=3.0, max_distance=12.0))

    payload = template.to_compact_json()
    restored = LayoutDeserializer.rebuild_template(payload)
    assert restored.template_id == "T-01"
    assert set(restored.elements) == {"brand_box", "title_box"}
    assert len(restored.constraints) == 1
    assert DataBindingResolver.resolve("erp.produit.marque", {"erp": {"produit": {"marque": "Acme"}}}, "Fallback") == "Acme"
    assert DataBindingResolver.resolve("erp.produit.unknown", {"erp": {"produit": {}}}, "Fallback") == "Fallback"

    engine = MultiTemplateImpositionEngine(page_w_mm=100.0, page_h_mm=100.0)
    placements = engine.arrange_mixed_templates([(40.0, 20.0, "A"), (20.0, 10.0, "B")])
    assert placements and placements[0][2] == "A"


def test_product_pum_print_spec_graphics_and_erp_data():
    from decimal import Decimal
    from datetime import datetime, timedelta
    from PLS_2 import (BarcodeElement, ERPMetadata, LabelDocument, PriceData,
                       PrintSpec, PrintStatus, ProductData, PromotionData)

    price = PriceData(sale_price=Decimal("5.00"))
    assert price.unit_price(Decimal("0.25"), "kg") == Decimal("20.00")
    product = ProductData(sku="SKU-1", commercial_name="Pommes",
                          net_quantity=Decimal("0.25"), net_unit="kg")
    promotion = PromotionData(advantage_text="+20% Credités",
                              discount_percent=Decimal("20"))
    barcode = BarcodeElement(field_id="ean", value="3760123456789",
                             x=2, y=2, width=40, height=12)
    erp = ERPMetadata(sku="SKU-1", print_status=PrintStatus.TO_PRINT)
    document = LabelDocument(80, 40, product=product, price_data=price,
                             promotion=promotion, print_spec=PrintSpec(),
                             system_data={"erp": erp.to_dict()})
    document.add_graphic(barcode)
    payload = document.to_json()
    assert "Pommes" in payload and "EAN13" in payload
    assert document.validate().valid
