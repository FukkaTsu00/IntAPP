# Compte rendu – Entraînement et comparaison de modèles

**Nom et prénom :** Alaaeddine Bakkar  
**Groupe :** G1  
**Date :** 21/10/2026

## 1. Objectif

L'objectif de ce TP est de compléter le projet `monprojet` afin d'entraîner plusieurs modèles de régression, de les comparer à une baseline sur un jeu de test, puis de sauvegarder le meilleur modèle selon la métrique principale définie dans `config.py`. 

## 2. Structure du projet

| Fichier | Rôle |
| :-- | :-- |
| `monprojet/config.py` | Paramètres : `TASK`, `TARGET`, `DATA_PATH`, `SPLIT`, `TEST_SIZE`, `SEED`, `MAIN_METRIC`, `MODELS_DIR`, etc. |
| `monprojet/data.py` | Fonctions `load_data()` et `split()`. |
| `monprojet/models.py` | Définition des candidats de modèles via `candidates()`. |
| `monprojet/train.py` | `build_preprocessing()` (fournie), `evaluate()` et `main()`. |

Lancement depuis la racine du projet : 

```bash
python -m monprojet.train
```

## 3. Travail réalisé

### 3.1 `load_data()`
- Lit le chemin des données depuis `config.DATA_PATH` (ou l'argument passé).
- Lève une `ValueError` explicite si la colonne cible `config.TARGET` est absente du jeu de données.
- Supprime les lignes où la valeur de la cible est manquante.

### 3.2 `split()`
- `X` correspond aux colonnes retournées par `feature_columns(df)`, `y` correspond à la colonne cible.
- **Mode utilisé :** `random` (découpage aléatoire).
- `train_test_split` est appliqué avec `test_size = config.TEST_SIZE`, `random_state = config.SEED`.
- Le prétraitement et l'apprentissage se font uniquement sur le jeu d'entraînement afin d'éviter toute fuite d'information vers le jeu de test.

### 3.3 `candidates()`

| Nom | Modèle | Rôle |
| :-- | :-- | :-- |
| `baseline` | `DummyRegressor(strategy="mean")` | Référence : prédit toujours la valeur moyenne de la cible sur le jeu d'entraînement |
| `regression_lineaire` | `LinearRegression()` | Modèle linéaire, simple et interprétable |
| `ridge` | `Ridge()` | Régression linéaire régularisée (L2) pour limiter le sur-apprentissage |
| `knn` | `KNeighborsRegressor()` | Méthode non-linéaire basée sur les plus proches voisins |
| `random_forest` | `RandomForestRegressor(n_estimators=200)` | Ensemble d'arbres en bagging |
| `gradient_boosting` | `GradientBoostingRegressor()` | Ensemble d'arbres en boosting |

Les modèles à composante aléatoire reçoivent `random_state = config.SEED` afin d'assurer la reproductibilité des résultats.

### 3.4 Prétraitement (`build_preprocessing()`, fourni)

Chaque modèle est intégré dans un `Pipeline` précédé d'un `ColumnTransformer` :

- **Colonnes numériques** : imputation par la médiane puis `StandardScaler`.
- **Colonnes catégorielles** : imputation par la modalité la plus fréquente puis `OneHotEncoder`.
- **Colonne texte éventuelle** : `TfidfVectorizer`.

Le prétraitement est appris uniquement sur le jeu d'entraînement. L'intégralité du pipeline (prétraitement + modèle) est ensuite sauvegardée.

### 3.5 `evaluate()` et `main()`

- **Régression** : `mae`, `rmse`, `r2`.
- Les valeurs sont converties en `float` et arrondies à 3 décimales.
- `main()` charge et découpe les données, entraîne et évalue l'ensemble des candidats, trie le tableau selon `config.MAIN_METRIC` dans le sens défini par `HIGHER_IS_BETTER`, sélectionne le meilleur modèle, puis le sauvegarde.
- Sauvegarde effectuée dans `config.MODELS_DIR` : `model.joblib` (pipeline complet entraîné) et `metrics.json` (métrique principale, meilleur modèle et scores de l'ensemble des modèles).

## 4. Résultats

**Jeu de données :** 340 lignes au total — 272 pour l'entraînement, 68 pour le test.  
**Tâche :** Régression  
**Métrique principale :** `MAE` (Mean Absolute Error) — plus faible est meilleur.

### Comparaison sur le jeu de test

| Modèle | MAE | RMSE | R² |
| :-- | :-- | :-- | :-- |
| `regression_lineaire` | 22.239 | 28.170 | 0.883 |
| `ridge` | 22.623 | 28.545 | 0.880 |
| `random_forest` | 31.825 | 41.647 | 0.745 |
| `knn` | 38.441 | 48.229 | 0.657 |
| `gradient_boosting` | 39.015 | 51.049 | 0.616 |
| `baseline` | 70.271 | 88.416 | -0.151 |

**Meilleur modèle :** `regression_lineaire` avec un `MAE = 22.239`.  
**Sauvegarde :** `models/model.joblib` et `models/metrics.json`.

## 5. Analyse

- **Net gain par rapport à la baseline.** Tous les modèles linéaires et ensemblistes battent largement la baseline. Le passage du modèle naïf (prédiction par la moyenne) au meilleur modèle permet de diviser l'erreur absolue moyenne par plus de 3 (de 70.271 à 22.239).
- **Régression linéaire performante.** La `regression_lineaire` obtient les meilleurs résultats sur l'ensemble des métriques. Avec un `R² = 0.883`, elle explique environ 88,3 % de la variance de la variable cible sur le jeu de test.
- **Régularisation peu nécessaire ici.** `Ridge` est très proche de la régression linéaire, avec une légère dégradation du MAE (+0,384). Cela suggère que le risque de sur-ajustement lié à la colinéarité est limité sur ce jeu de données.
- **Modèles non-linéaires moins performants.** `Random Forest`, `KNN` et `Gradient Boosting` sont nettement moins bons que les modèles linéaires dans cette configuration. Cela indique que la relation entre les variables explicatives et la cible est majoritairement linéaire.
- **Cohérence entre les métriques.** L'ordre de classement est identique pour le MAE et le RMSE, ce qui renforce la fiabilité de la sélection du meilleur modèle.

## 6. Limites et pistes d'amélioration

- **Un seul découpage train/test.** Une validation croisée (k-fold) permettrait d'obtenir une estimation plus stable des performances et de mieux juger de la généralisation des modèles.
- **Réglages par défaut.** Les hyperparamètres utilisés sont ceux par défaut. Un `GridSearchCV` ou `RandomizedSearchCV` pourrait permettre d'optimiser `Ridge`, `Random Forest` ou `Gradient Boosting` et potentiellement améliorer leurs résultats.
- **Analyse des résidus.** Il serait pertinent d'étudier les résidus de la régression linéaire (homoscédasticité, normalité, valeurs aberrantes) afin de valider les hypothèses du modèle et d'identifier d'éventuelles améliorations.
- **Ingénierie des features.** L'exploration de transformations (interactions, polynômes) ou d'une sélection de variables pourrait aider les modèles non-linéaires à se rapprocher, voire à dépasser, les performances actuelles.

## 7. Conclusion

Le pipeline complet (chargement, découpage, prétraitement, entraînement, évaluation, sélection et sauvegarde) est fonctionnel et reproductible.

Sur ce jeu de données, **la régression linéaire est retenue comme meilleur modèle** avec un `MAE = 22.239`, un `RMSE = 28.170` et un `R² = 0.883`. Elle surpasse nettement la baseline et se montre plus adaptée que les approches non-linéaires testées.

Le pipeline complet ainsi que les métriques sont sauvegardés respectivement dans `models/model.joblib` et `models/metrics.json`.