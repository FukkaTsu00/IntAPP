"""Entraîne chaque modèle candidat, l'évalue sur le jeu de test et les compare.

Usage, depuis la racine du projet : python -m monprojet.train
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error, mean_squared_error,
                             precision_score, r2_score, recall_score)
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from monprojet import config
from monprojet.data import load_data, split
from monprojet.models import candidates

HIGHER_IS_BETTER = {"accuracy": True, "recall": True, "precision": True, "f1": True,
                    "mae": False, "rmse": False, "r2": True}


def build_preprocessing(X: pd.DataFrame) -> ColumnTransformer:
    """Prépare les colonnes : nombres mis à l'échelle, catégories encodées, texte vectorisé. (Fournie.)"""
    text = [config.TEXT_COLUMN] if config.TEXT_COLUMN else []
    numeric = [c for c in X.columns if c not in text and pd.api.types.is_numeric_dtype(X[c])]
    categorical = [c for c in X.columns if c not in text and c not in numeric]
    steps = []
    if numeric:
        steps.append(("nombres", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric))
    if categorical:
        steps.append(("categories", make_pipeline(SimpleImputer(strategy="most_frequent"),
                                                  OneHotEncoder(handle_unknown="ignore")), categorical))
    if text:
        steps.append(("texte", TfidfVectorizer(), config.TEXT_COLUMN))
    return ColumnTransformer(steps, sparse_threshold=0)


def _r(value) -> float:
    """Convertit en float Python (sérialisable en JSON) arrondi à 3 décimales."""
    return round(float(value), 3)


def evaluate(model, X_test, y_test) -> dict:
    """Prédit sur le jeu de test et renvoie un dictionnaire {nom de la métrique: valeur}.

    - classification : "accuracy", "recall", "precision", "f1"
      (average="binary" s'il y a deux classes, "macro" sinon ; zero_division=0) ;
    - régression : "mae", "rmse", "r2" ;
    - des float, arrondis à 3 décimales.
    """
    y_pred = model.predict(X_test)

    if config.TASK == "classification":
        classes = np.unique(y_test)
        if len(classes) == 2:
            # Classe positive : 1 si elle existe (0/1, False/True), sinon la plus grande étiquette
            pos_label = 1 if 1 in classes else classes[-1]
            options = {"average": "binary", "pos_label": pos_label, "zero_division": 0}
        else:
            options = {"average": "macro", "zero_division": 0}
        return {
            "accuracy": _r(accuracy_score(y_test, y_pred)),
            "recall": _r(recall_score(y_test, y_pred, **options)),
            "precision": _r(precision_score(y_test, y_pred, **options)),
            "f1": _r(f1_score(y_test, y_pred, **options)),
        }

    if config.TASK == "regression":
        return {
            "mae": _r(mean_absolute_error(y_test, y_pred)),
            "rmse": _r(np.sqrt(mean_squared_error(y_test, y_pred))),
            "r2": _r(r2_score(y_test, y_pred)),
        }

    raise ValueError(
        f"TASK inconnue : {config.TASK!r}. Valeurs possibles : 'classification' ou 'regression'."
    )


def main() -> None:
    """Entraîne chaque candidat, l'évalue, compare, et sauvegarde."""
    metric = config.MAIN_METRIC
    if metric not in HIGHER_IS_BETTER:
        raise ValueError(
            f"MAIN_METRIC inconnue : {metric!r}. Valeurs possibles : {list(HIGHER_IS_BETTER)}."
        )
    higher_is_better = HIGHER_IS_BETTER[metric]

    # 1. Données
    df = load_data()
    X_train, X_test, y_train, y_test = split(df)
    print(f"Données : {len(df)} lignes — entraînement {len(X_train)}, test {len(X_test)}")

    # 2. Entraîner sur l'entraînement, évaluer sur le test (le même pour tous)
    resultats = {}
    modeles = {}
    for nom, estimateur in candidates().items():
        model = Pipeline([
            ("preparation", build_preprocessing(X_train)),
            ("modele", estimateur),
        ])
        model.fit(X_train, y_train)
        resultats[nom] = evaluate(model, X_test, y_test)
        modeles[nom] = model

    # 3. Tableau de comparaison, trié selon la métrique principale
    tableau = pd.DataFrame(resultats).T
    if metric not in tableau.columns:
        raise ValueError(
            f"MAIN_METRIC = {metric!r} ne correspond pas à TASK = {config.TASK!r} "
            f"(métriques calculées : {list(tableau.columns)})."
        )
    tableau = tableau.sort_values(metric, ascending=not higher_is_better)
    print(f"\nComparaison sur le jeu de test (métrique principale : {metric})\n")
    print(tableau.to_string())

    # 4. Meilleur modèle selon la métrique principale
    best = tableau[metric].idxmax() if higher_is_better else tableau[metric].idxmin()
    baseline_name = next(iter(resultats))  # la baseline est le premier candidat
    print(
        f"\nMeilleur modèle : {best} ({metric} = {resultats[best][metric]}) — "
        f"baseline : {resultats[baseline_name][metric]}"
    )

    # 5. Sauvegarde
    models_dir = Path(config.MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(modeles[best], models_dir / "model.joblib")
    metrics = {"main_metric": metric, "best": best, "results": resultats}
    (models_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Modèle sauvegardé dans {models_dir / 'model.joblib'}, métriques dans {models_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()