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
