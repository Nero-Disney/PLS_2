# PLS_2

Editeur Qt de textes enrichis et moteur de labels imprimables, organisé en modules par responsabilité.

## Vue d'ensemble

Le projet est désormais structuré en packages fonctionnels :

- `editor/` : modèle texte, cursor, layout, vue et textbox interactives ;
- `core/` : modèle métier, validation, données produit, documents d'étiquette ;
- `fields/` : champs métier spécialisés pour les labels ;
- `template/` : moteur de templates, contraintes et sérialisation prefab ;
- `print_system/` : impression native, PDF et paramètres d'impression ;
- `app/` : bootstrap applicatif de démonstration ;
- `tests/` : validation de régression et smoke tests.

## Fonctionnalités principales

- édition de texte, sélection, clavier et souris ;
- paragraphes, format par caractère, gras / italique / soulignement ;
- alignement vertical, puces et retour à la ligne ;
- boîte de texte avec poignées de redimensionnement et rotation ;
- modes de débordement : `CLIP`, `VISIBLE`, `AUTOFIT_SHRINK`, `AUTOFIT_GROW` ;
- modes de dimensionnement : `AUTO_FIT_CONTENT`, `FREE_RESIZE`, `LOCKED` ;
- conversions physiques en pixels / mm / points avec DPI explicite ;
- placeholder, mise en page automatique et redimensionnement adaptatif ;
- validation métier de labels, sérialisation JSON et données ERP ;
- impression directe et export PDF ;
- templates prefab, contraintes visuelles et binding de données.

## Démarrage

Depuis le dossier parent du projet, on peut lancer l'application de démonstration :

```bash
python -m PLS_2.app.final_app
```

Ou, depuis le dossier du projet :

```bash
python app/final_app.py
```

La logique métier n'est pas dans le script de lancement ; l'application sert uniquement de bootstrap.

## API publique

Exemple simple :

```python
from PLS_2 import TextBox

box = TextBox(text="Bonjour", x=20, y=20, width=420, height=220)
box.set_text("Nouveau texte")
box.resize_box(500, 260)
```

Utilisation en unités physiques :

```python
from PLS_2 import TextBox

box = TextBox(text="Prix", x=10, y=5, width=50, height=20,
              unit="mm", dpi=300, sizing="free_resize")
```

## Modèle de document / label

Le domaine de label peut être préparé sans lancer Qt :

```python
from PLS_2 import BarcodeField, LabelDocument, PriceValue

label = LabelDocument(width=80, height=50, unit="mm", dpi=300)
label.add(PriceValue(field_id="price", value="12.995", x=40, y=20,
                    width=30, height=12))
label.add(BarcodeField(field_id="ean", value="3760123456789",
                      x=5, y=35, width=50, height=10))

diagnostic = label.validate()
saved = label.to_json(indent=2)
restored = LabelDocument.from_json(saved)
```

## Impression

```python
from PLS_2 import LabelDocument, LabelPrinter, PriceValue

label = LabelDocument(80, 50, unit="mm")
label.add(PriceValue(field_id="price", value="9.99", x=10, y=20,
                    width=30, height=10))

printer = LabelPrinter(label)
printer.print_direct()
printer.export_pdf("etiquette.pdf")
```

Le moteur d'impression est séparé de l’éditeur : `print_system/` gère les paramètres de sortie, le rendu et le PDF, tandis que `editor/` gère les widgets de saisie.

## Champs métier et templates

Les champs de labels héritent de `TextBox` et ajoutent simplement des règles métier :

```python
from PLS_2 import BRAND, DESCRIPTION, PARTNO, PRICE

brand = BRAND("Acme")
description = DESCRIPTION("Produit longue durée")
part_number = PARTNO("AC-2048")
price = PRICE("12,995", currency="EUR", decimals=2)
```

Les templates prefab sont disponibles dans `template/` :

```python
from PLS_2 import PrefabLabelTemplate, OptimizedElement, GraphicConstraint, BoxEdge
```

## Tests

```bash
cd /workspaces/PLS_2
PYTHONPATH=/workspaces pytest -q
```

ou, selon l’environnement :

```bash
pytest -q
```

Le package est conçu pour être utilisé dans un environnement sans affichage avec la plateforme Qt `offscreen`.

## Structure du dépôt

```text
PLS_2/
├── __init__.py
├── app/
│   ├── __init__.py
│   ├── demo.py
│   └── final_app.py
├── core/
│   ├── __init__.py
│   ├── label_design.py
│   ├── label_document.py
│   ├── label_elements.py
│   ├── label_erp.py
│   ├── label_graphics.py
│   ├── label_product.py
│   ├── label_styles.py
│   ├── label_validation.py
│   └── printing.py
├── editor/
│   ├── __init__.py
│   ├── cursor.py
│   ├── layout.py
│   ├── layout_engine.py
│   ├── model.py
│   ├── textbox.py
│   ├── units.py
│   └── view.py
├── fields/
│   ├── __init__.py
│   └── label_fields.py
├── print_system/
│   ├── __init__.py
│   ├── label_printing.py
│   └── printing.py
├── template/
│   ├── __init__.py
│   ├── engine_label_system.py
│   ├── label_engine.py
│   └── label_template.py
├── tests/
│   ├── __init__.py
│   ├── test_headless.py
│   └── test_view_regressions.py
├── README.md
├── start_gui.sh
└── LICENSE
```

La séparation suit le principe : 
- `editor` pour l’interaction ;
- `core` pour le métier ;
- `template` pour les modèles imprimables et prefab ;
- `print_system` pour la sortie ;
- `app` pour le démarrage ;
- `tests` pour la validation.
