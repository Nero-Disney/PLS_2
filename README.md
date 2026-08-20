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
