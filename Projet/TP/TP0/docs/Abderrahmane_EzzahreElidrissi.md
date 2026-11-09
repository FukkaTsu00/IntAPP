# Compte rendu – Entraînement et comparaison de modèles

**Nom et prénom :** Abderrahmane Ezzahre Elidrissi  
**Groupe :** G2  
**Date :** 27/10/2026

## 1. Objectif

L'objectif de ce TP est de compléter le projet `monprojet` afin d'entraîner plusieurs modèles de classification pour la prédiction de pannes d'équipements, de les comparer à une baseline sur un jeu de test, puis de sauvegarder le meilleur modèle selon la métrique principale définie dans `config.py`. Le modèle doit aider un technicien ou un responsable de maintenance à décider s'il faut intervenir préventivement sur un équipement, à partir de relevés de capteurs.

## 2. Structure du projet

| Fichier | Rôle |
| :-- | :-- |
| `monprojet/config.py` | Paramètres : `TASK`, `TARGET`, `DATA_PATH`, `SPLIT`, `TIME_COLUMN`, `TEST_SIZE`, `SEED`, `MAIN_METRIC`, `MODELS_DIR`, etc. |
| `monprojet/data.py` | Fonctions `load_data()` et `split()`. |
| `monprojet/models.py` | Définition des candidats de modèles via `candidates()`. |
| `monprojet/train.py` | `build_preprocessing()` (fournie), `evaluate()` et `main()`. |

Lancement depuis la racine du projet :

```bash
python -m monprojet.train
```

## 3. Travail réalisé

### 3.1 `load_data()`
- Charge le fichier `data/exemple_pannes.csv` (chemin lu dans `config.DATA_PATH`).
- Vérifie la présence de la colonne cible `config.TARGET`. *(à confirmer selon votre code)*
- Supprime les lignes dont la cible est manquante. *(à confirmer selon votre code)*

### 3.2 `split()`
- `X` correspond aux colonnes retournées par `feature_columns(df)`, `y` correspond à la colonne cible.
- Le découpage suit le mode défini par `SPLIT` (et `TIME_COLUMN` s'il s'agit d'une série temporelle). **Mode utilisé :** *(à compléter : `random` ou `time`)*.
- Le prétraitement et l'apprentissage se font uniquement sur le jeu d'entraînement afin d'éviter toute fuite d'information vers le jeu de test.

### 3.3 `candidates()`

| Nom | Modèle | Rôle |
| :-- | :-- | :-- |
| `baseline` | `DummyClassifier(strategy="most_frequent")` | Référence : prédit toujours la classe majoritaire (pas de panne) |
| `logistic_regression` | Régression logistique | Modèle linéaire, simple et interprétable |
| `decision_tree` | Arbre de décision | Modèle à base de règles de décision, capture des interactions entre capteurs |
| `random_forest` | Forêt aléatoire | Ensemble d'arbres en bagging |

La baseline est placée en tête de `candidates()`. Les modèles à composante aléatoire reçoivent `random_state = config.SEED` afin d'assurer la reproductibilité des résultats. *(à confirmer, ainsi que les hyperparamètres éventuels)*

### 3.4 Prétraitement (`build_preprocessing()`, fourni)

Chaque modèle est intégré dans un `Pipeline` précédé d'un `ColumnTransformer` :

- **Colonnes numériques** : imputation par la médiane puis `StandardScaler`.
- **Colonnes catégorielles** : imputation par la modalité la plus fréquente puis `OneHotEncoder`.
- **Colonne texte éventuelle** : `TfidfVectorizer`.

Le prétraitement est appris uniquement sur le jeu d'entraînement. L'intégralité du pipeline (prétraitement + modèle) est ensuite sauvegardée.

### 3.5 `evaluate()` et `main()`

- **Classification** : `accuracy`, `recall`, `precision`, `f1`.
- **Métrique principale : `recall`** (`MAIN_METRIC = "recall"`). Elle mesure la part des pannes réelles effectivement détectées : c'est celle qui pénalise les faux négatifs, dont le coût est le plus élevé (immobilisation, réparation urgente, impact sur la production et la sécurité). Un faux positif, lui, ne coûte qu'une intervention inutile.
- `main()` charge et découpe les données, entraîne et évalue l'ensemble des candidats, trie le tableau selon `config.MAIN_METRIC`, sélectionne le meilleur modèle, puis le sauvegarde.
- Sauvegarde effectuée dans `config.MODELS_DIR` : `model.joblib` (pipeline complet entraîné) et `metrics.json` (scores de tous les modèles).

## 4. Résultats

**Jeu de données :** `data/exemple_pannes.csv` — *(à compléter : nombre de lignes au total, lignes d'entraînement, lignes de test)*  
**Tâche :** Classification binaire (panne / pas de panne)  
**Métrique principale :** `recall` — plus élevé est meilleur.  
**Critère d'acceptation :** le `recall` du modèle retenu doit dépasser celui de la baseline sur le jeu de test.

### Comparaison sur le jeu de test

| Modèle | accuracy | recall | precision | f1 |
| :-- | :-- | :-- | :-- | :-- |
| `decision_tree` | 0.839 | **0.597** | 0.538 | 0.566 |
| `logistic_regression` | 0.889 | 0.574 | 0.737 | 0.645 |
| `random_forest` | 0.873 | 0.545 | 0.671 | 0.602 |
| `baseline` | 0.824 | 0.000 | 0.000 | 0.000 |

**Meilleur modèle :** `decision_tree` avec un `recall = 0.597`.  
**Sauvegarde :** `models/model.joblib` et `models/metrics.json`.

## 5. Analyse

- **Gain net par rapport à la baseline.** La baseline obtient 0.824 d'accuracy sans détecter aucune panne (`recall = 0`) : l'accuracy est trompeuse sur un jeu déséquilibré, puisque prédire toujours « pas de panne » donne déjà un bon score. Le modèle retenu détecte environ 60 % des pannes réelles (+0.597 de recall), ce qui valide le critère d'acceptation.
- **Choix cohérent avec la métrique principale.** `decision_tree` a le meilleur `recall` (0.597), même s'il a la plus faible `precision` (0.538) : il déclenche donc plus de fausses alertes. Ce compromis est acceptable ici, car un faux négatif coûte bien plus cher qu'une intervention inutile.
- **Autres modèles plus équilibrés.** `logistic_regression` obtient la meilleure accuracy (0.889), la meilleure precision (0.737) et le meilleur f1 (0.645), tandis que `random_forest` a également une meilleure accuracy et un meilleur f1 que `decision_tree`. Si l'on valorisait l'équilibre entre fausses alertes et pannes manquées plutôt que le recall seul, le choix pourrait être différent.
- **Écarts de recall faibles.** Les trois modèles sont proches (0.545 à 0.597) : avec un seul découpage, rien ne garantit que `decision_tree` soit durablement meilleur que `logistic_regression`.

## 6. Limites et pistes d'amélioration

- **Un seul découpage train/test.** Une validation croisée permettrait d'obtenir une estimation plus stable des performances et de départager des modèles dont les scores sont proches.
- **Réglages par défaut.** Les hyperparamètres ne sont pas optimisés ; un `GridSearchCV` ou `RandomizedSearchCV` pourrait améliorer les modèles.
- **Seuil de décision et déséquilibre des classes.** Ajuster le seuil de décision ou utiliser `class_weight` pourrait augmenter le recall sans trop dégrader la precision.
- **Taille et qualité des données.** Les performances sont limitées par le jeu fourni, avec un risque de surapprentissage si les données sont peu nombreuses, et une hypothèse de représentativité non vérifiée.
- **Hors périmètre.** Déploiement en production, monitoring, explicabilité poussée et optimisation temps réel. Le modèle reste un outil d'aide à la décision, non un substitut à un diagnostic métier.

## 7. Conclusion

Le pipeline complet (chargement, découpage, prétraitement, entraînement, évaluation, sélection et sauvegarde) est fonctionnel et reproductible.

Sur ce jeu de données, **`decision_tree` est retenu comme meilleur modèle** selon la métrique principale, avec un `recall = 0.597`, contre 0.0 pour la baseline. Le critère d'acceptation est atteint. Les résultats restent toutefois proches de ceux de `logistic_regression` et de `random_forest`, et devraient être confirmés par une validation croisée.

Le pipeline complet ainsi que les métriques sont sauvegardés respectivement dans `models/model.joblib` et `models/metrics.json`.
