# TP : entraîner et comparer des modèles de régression

**Nom et prénom :** Othmane Ettayam
**Groupe :** G1
**Date :** 21/10/2026

---

## 1. Objectif

Dans ce TP, je complète le projet `monprojet` pour entraîner plusieurs modèles de régression, les comparer à une baseline sur un jeu de test, puis sauvegarder le meilleur selon la métrique principale définie dans `config.py`.

## 2. Structure du projet

| Fichier | Rôle |
| :-- | :-- |
| `monprojet/config.py` | Les paramètres : `TASK`, `TARGET`, `DATA_PATH`, `SPLIT`, `TEST_SIZE`, `SEED`, `MAIN_METRIC`, `MODELS_DIR`, etc. |
| `monprojet/data.py` | Les fonctions `load_data()` et `split()`. |
| `monprojet/models.py` | La liste des modèles candidats, via `candidates()`. |
| `monprojet/train.py` | `build_preprocessing()` (fournie), `evaluate()` et `main()`. |

Pour lancer l'entraînement, depuis la racine du projet :

```bash
python -m monprojet.train
```

## 3. Ce que j'ai écrit

### 3.1 `load_data()`

- Lit les données à l'emplacement `config.DATA_PATH` (ou à celui passé en argument).
- Lève une `ValueError` claire si la colonne cible `config.TARGET` n'existe pas dans le jeu de données.
- Supprime les lignes dont la cible est manquante.

### 3.2 `split()`

- `X` regroupe les colonnes renvoyées par `feature_columns(df)`, et `y` est la colonne cible.
- **Mode utilisé :** `random`, c'est-à-dire un découpage aléatoire.
- J'applique `train_test_split` avec `test_size = config.TEST_SIZE` et `random_state = config.SEED`.
- Le prétraitement et l'apprentissage ne voient que le jeu d'entraînement, pour qu'aucune information du jeu de test ne « fuite » vers le modèle.

### 3.3 `candidates()`

| Nom | Modèle | Pourquoi |
| :-- | :-- | :-- |
| `baseline` | `DummyRegressor(strategy="mean")` | Point de comparaison : prédit toujours la moyenne de la cible calculée sur l'entraînement |
| `regression_lineaire` | `LinearRegression()` | Modèle linéaire, simple et facile à interpréter |
| `ridge` | `Ridge()` | Régression linéaire régularisée (L2), pour limiter le sur-apprentissage |
| `knn` | `KNeighborsRegressor()` | Modèle non linéaire qui s'appuie sur les plus proches voisins |
| `random_forest` | `RandomForestRegressor(n_estimators=200)` | Ensemble d'arbres construits en bagging |
| `gradient_boosting` | `GradientBoostingRegressor()` | Ensemble d'arbres construits en boosting |

Les modèles qui ont une part d'aléatoire reçoivent `random_state = config.SEED`, pour retrouver les mêmes résultats à chaque exécution.

### 3.4 Prétraitement (`build_preprocessing()`, fournie)

Chaque modèle est placé dans un `Pipeline`, précédé d'un `ColumnTransformer` :

- **Colonnes numériques :** imputation par la médiane, puis `StandardScaler`.
- **Colonnes catégorielles :** imputation par la modalité la plus fréquente, puis `OneHotEncoder`.
- **Colonne de texte (s'il y en a une) :** `TfidfVectorizer`.

Le prétraitement est appris sur l'entraînement uniquement. C'est le pipeline entier (prétraitement + modèle) qui est sauvegardé ensuite.

### 3.5 `evaluate()` et `main()`

- **Métriques de régression :** `mae`, `rmse`, `r2`, converties en `float` et arrondies à 3 décimales.
- `main()` charge et découpe les données, entraîne et évalue tous les candidats, trie le tableau selon `config.MAIN_METRIC` (dans le sens indiqué par `HIGHER_IS_BETTER`), retient le meilleur modèle et le sauvegarde.
- Dans `config.MODELS_DIR`, j'enregistre `model.joblib` (le pipeline complet entraîné) et `metrics.json` (la métrique principale, le meilleur modèle et les scores de tous les modèles).

## 4. Résultats

- **Données :** 340 lignes, dont 272 pour l'entraînement et 68 pour le test.
- **Tâche :** régression.
- **Métrique principale :** `MAE` (erreur absolue moyenne), plus elle est basse, mieux c'est.

### Comparaison sur le jeu de test

| Modèle | MAE | RMSE | R² |
| :-- | :-- | :-- | :-- |
| `regression_lineaire` | 22.239 | 28.170 | 0.883 |
| `ridge` | 22.623 | 28.545 | 0.880 |
| `random_forest` | 31.825 | 41.647 | 0.745 |
| `knn` | 38.441 | 48.229 | 0.657 |
| `gradient_boosting` | 39.015 | 51.049 | 0.616 |
| `baseline` | 70.271 | 88.416 | -0.151 |

**Meilleur modèle :** `regression_lineaire`, avec une `MAE` de 22.239.
**Fichiers sauvegardés :** `models/model.joblib` et `models/metrics.json`.

## 5. Analyse

- **Tous les modèles font mieux que la baseline.** En passant de la prédiction par la moyenne (MAE de 70.271) au meilleur modèle (22.239), l'erreur absolue moyenne est divisée par plus de 3.
- **La régression linéaire gagne sur toute la ligne.** Elle a les meilleurs scores sur les trois métriques. Avec un `R²` de 0.883, elle explique environ 88,3 % de la variance de la cible sur le jeu de test.
- **La régularisation n'apporte presque rien ici.** `Ridge` est très proche de la régression linéaire, avec un MAE légèrement moins bon (+0,384). Le risque de sur-ajustement dû à la colinéarité semble donc faible sur ces données.
- **Les modèles non linéaires font moins bien.** `Random Forest`, `KNN` et `Gradient Boosting` sont nettement derrière les modèles linéaires. Cela laisse penser que le lien entre les variables explicatives et la cible est surtout linéaire.
- **Les métriques racontent la même histoire.** Le classement est identique pour la MAE et la RMSE, ce qui rend le choix du meilleur modèle plus fiable.

## 6. Limites et pistes d'amélioration

- **Un seul découpage train/test.** Une validation croisée (k-fold) donnerait une estimation plus stable et permettrait de mieux juger la capacité de généralisation.
- **Hyperparamètres par défaut.** Un `GridSearchCV` ou un `RandomizedSearchCV` pourrait améliorer `Ridge`, `Random Forest` ou `Gradient Boosting`.
- **Résidus à étudier.** Analyser les résidus de la régression linéaire (homoscédasticité, normalité, valeurs aberrantes) permettrait de vérifier ses hypothèses et de repérer des pistes d'amélioration.
- **Création de variables.** Des transformations (interactions, polynômes) ou une sélection de variables pourraient aider les modèles non linéaires à rattraper, voire dépasser, la régression linéaire.

## 7. Conclusion

Le pipeline complet fonctionne et donne les mêmes résultats d'une exécution à l'autre : chargement, découpage, prétraitement, entraînement, évaluation, sélection et sauvegarde.

Sur ce jeu de données, **je retiens la régression linéaire** : `MAE = 22.239`, `RMSE = 28.170`, `R² = 0.883`. Elle dépasse nettement la baseline et convient mieux que les approches non linéaires testées.

Le pipeline complet et les métriques sont enregistrés dans `models/model.joblib` et `models/metrics.json`.
