# PLS_2

Editeur Qt minimaliste de blocs de texte enrichis, avec mise en page par
paragraphe et interactions de type PowerPoint.

## Fonctionnalites

- edition de texte, selections par clavier et par glisser ;
- formats gras, italique, soulignement et couleurs par caractere ;
- alignement vertical, retour a la ligne et puces de paragraphe ;
- bounding box avec huit poignees de taille et une poignee de rotation ;
- deplacement, rotation avec `Shift` par pas de 15 degres et redimensionnement
  proportionnel avec `Shift` ;
- fond, bordure, transparence et coins arrondis ;
- modes `CLIP`, `VISIBLE`, `AUTOFIT_SHRINK` et `AUTOFIT_GROW` ;
- dimensionnement `AUTO_FIT_CONTENT`, `FREE_RESIZE` ou `LOCKED` ;
- dimensions d'API en pixels, millimetres ou points avec DPI explicite ;
- taille initiale calculée selon le contenu et le placeholder ;
- copier, couper, coller, annuler et retablir.

## Execution

```bash
python final_app.py
```

`demo.py` reste disponible comme lanceur rétrocompatible. Il ne contient pas
la textbox : l'implémentation est exposée par le package et l'application de
validation est isolée dans `final_app.py`.

## API simplifiee

```python
from PLS_2 import TextBox

box = TextBox(text="Bonjour", x=20, y=20, width=420, height=220)
box.set_text("Nouveau texte")
box.resize_box(500, 260)
```

Pour une composition imprimable, utiliser une unite physique et un DPI de
cible explicite :

```python
box = TextBox(text="Prix", x=10, y=5, width=50, height=20,
              unit="mm", dpi=300)
```

## Modele de design de label

Les donnees metier peuvent etre preparees sans lancer Qt :

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

## Impression directe

Le meme document peut etre imprime par le dialogue natif ou directement sur
la cible par defaut :

```python
from PLS_2 import LabelPrinter

printer = LabelPrinter(label)
printer.print_with_dialog()  # interface native de choix d'imprimante
printer.print_direct()       # flux sans dialogue
printer.export_pdf("etiquette.pdf")
```

Le module [printing.py](printing.py) reste independant des widgets d'edition.
Il configure la taille papier a partir des dimensions physiques du document et
utilise le meme repere pour l'aperçu PDF et l'impression.

Les responsabilites du domaine sont exposees par modules :

- [label_validation.py](label_validation.py) : erreurs, avertissements et diagnostics ;
- [label_styles.py](label_styles.py) : themes et styles nommes ;
- [label_elements.py](label_elements.py) : elements metier headless ;
- [label_document.py](label_document.py) : document et template imprimable ;
- [printing.py](printing.py) : impression native, directe et PDF.

`label_design.py` reste la facade de compatibilite historique pour les imports
existants.

Les validations distinguent les erreurs bloquantes des avertissements, par
exemple une valeur obligatoire absente, un champ hors etiquette ou deux champs
qui se chevauchent. `PriceValue` conserve la valeur numerique brute et genere
le texte localise uniquement pour l'affichage.

Les champs texte Qt (`Price`, `Brand`, `Description`, `PartNo`) restent utiles
pour l'edition interactive. Les modeles `LabelFieldModel`, `PriceValue` et
`BarcodeField` sont destines a la generation en lot, a la validation et a la
future sortie PDF/SVG sans widget.

Le modele produit couvre aussi les donnees reglementaires et commerciales :
`commercial_name`, `legal_name`, `brand`, `origin`, `variety`, `calibre`,
`category`, `ingredients`, `allergens`, `sanitary_stamp`, quantite nette et
unite de reference. `PriceData` calcule le prix a l'unite de mesure, tandis
que `PromotionData` gere l'avantage fidelite, la remise et la mention de
shrinkflation.

Les parametres d'impression sont portes par `PrintSpec` : gabarit, support,
orientation, mode couleur, DPI, fond perdu, marge de securite, planche,
nombre de copies, ordre de tri et statut (`to_print`, `printed`, `error`).
Les metadonnees ERP (`ERPMetadata`) conservent SKU, rayon, emplacement,
fournisseur et dates de validite.

Les elements graphiques sont distincts des textboxes : `BarcodeElement`,
`LogoElement`, `PictogramElement` et `GraphicElement` representent les assets,
QR codes, labels officiels, Nutri-Score/Eco-Score et fonds promotionnels.

Des champs metier sont egalement disponibles pour les templates d'etiquettes :

```python
from PLS_2 import BRAND, CURRENCY, DESCRIPTION, PARTNO, PRICE

brand = BRAND("Acme")
description = DESCRIPTION("Produit longue duree")
part_number = PARTNO("AC-2048")
price = PRICE("12,995", currency="EUR", decimals=2)
currency = CURRENCY("EUR")
```

Chaque champ herite de `TextBox`, conserve les memes poignées et modes de
dimensionnement, et ajoute uniquement ses parametres metier et son style par
defaut. `PRICE` normalise le nombre avec arrondi decimal explicite.

La taille peut etre controlee avec `sizing="auto_fit_content"` (defaut),
`sizing="free_resize"` ou `sizing="locked"`. Un redimensionnement manuel
fait passer une textbox auto-fit en redimensionnement libre. Le placeholder
est defini avec `placeholder="Saisissez un titre"` et sert aussi a calculer la
taille initiale lorsque le texte est vide.

`TextBox` est la facade recommandee. `TextObject`, `TextCursor`, `LayoutEngine`
et `TextObjectView` restent disponibles pour les integrations avancees et la
compatibilite avec le code existant.

Dans un environnement sans affichage, Qt utilise automatiquement la plateforme
`offscreen` pour les tests.

## Tests

```bash
pytest -q
```

Le modele conserve la position, la taille et la rotation de chaque objet.
La vue applique la transformation inverse aux clics afin que le caret, la
selection et les poignees restent coherents avec un objet tourne.
