"""Les modèles à comparer.

candidates() renvoie la baseline en premier, puis les modèles candidats adaptés à config.TASK.
"""
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor

from monprojet import config


def candidates() -> dict:
    """Renvoie un dictionnaire {nom: modèle scikit-learn non entraîné}.

    - le PREMIER modèle est la baseline (DummyClassifier / DummyRegressor) ;
    - puis au moins trois vrais modèles adaptés à config.TASK ;
    - random_state=config.SEED pour les modèles qui ont du hasard.
    """
    if config.TASK == "classification":
        return {
            # Baseline : prédit toujours la classe la plus fréquente
            "baseline": DummyClassifier(strategy="most_frequent"),
            "regression_logistique": LogisticRegression(
                max_iter=1000, random_state=config.SEED
            ),
            # Pour aller plus loin : pénalise davantage les erreurs sur la classe rare
            "regression_logistique_equilibree": LogisticRegression(
                max_iter=1000, class_weight="balanced", random_state=config.SEED
            ),
            "knn": KNeighborsClassifier(n_neighbors=15),
            "random_forest": RandomForestClassifier(
                n_estimators=200, random_state=config.SEED, n_jobs=-1
            ),
            "gradient_boosting": HistGradientBoostingClassifier(random_state=config.SEED),
        }

    if config.TASK == "regression":
        return {
            # Baseline : prédit toujours la moyenne de la cible d'entraînement
            "baseline": DummyRegressor(strategy="mean"),
            "regression_lineaire": LinearRegression(),
            "ridge": Ridge(alpha=1.0, random_state=config.SEED),
            "knn": KNeighborsRegressor(n_neighbors=15),
            "random_forest": RandomForestRegressor(
                n_estimators=200, random_state=config.SEED, n_jobs=-1
            ),
            "gradient_boosting": HistGradientBoostingRegressor(random_state=config.SEED),
        }

    raise ValueError(
        f"TASK inconnue : {config.TASK!r}. Valeurs possibles : 'classification' ou 'regression'."
    )