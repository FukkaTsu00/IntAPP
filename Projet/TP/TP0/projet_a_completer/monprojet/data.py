"""Chargement et découpage des données.

load_data() lit le CSV défini dans config.py ; split() sépare entraînement / test
selon config.SPLIT. Aucun nom de colonne ni chemin n'est écrit en dur ici.
"""
import math
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from monprojet import config


def load_data(path=None) -> pd.DataFrame:
    """Lit le fichier CSV et renvoie un DataFrame.

    - lit config.DATA_PATH (ou `path` s'il est donné) ;
    - lève une ValueError si la colonne config.TARGET n'existe pas ;
    - retire les lignes où la cible est manquante.
    """
    path = Path(path) if path is not None else Path(config.DATA_PATH)
    df = pd.read_csv(path)

    if config.TARGET not in df.columns:
        raise ValueError(
            f"La colonne cible '{config.TARGET}' est absente du fichier {path}. "
            f"Colonnes disponibles : {list(df.columns)}. "
            "Vérifiez TARGET dans config.py (ou le séparateur du CSV)."
        )

    df = df.dropna(subset=[config.TARGET]).reset_index(drop=True)
    return df


def feature_columns(df: pd.DataFrame) -> list:
    """Les colonnes d'entrée : celles de config.FEATURES, ou toutes sauf la cible et la date. (Fournie.)"""
    if config.FEATURES is not None:
        return list(config.FEATURES)
    excluded = {config.TARGET, config.TIME_COLUMN}
    return [c for c in df.columns if c not in excluded]


def split(df: pd.DataFrame):
    """Renvoie X_train, X_test, y_train, y_test.

    - X = les colonnes de feature_columns(df) ; y = la colonne cible ;
    - "random" : découpage aléatoire (config.TEST_SIZE, config.SEED),
      stratifié sur y pour une classification ;
    - "chronologique" : tri selon config.TIME_COLUMN, les lignes les plus
      récentes vont dans le test.
    """
    X = df[feature_columns(df)]
    y = df[config.TARGET]

    if config.SPLIT == "random":
        stratify = y if config.TASK == "classification" else None
        return train_test_split(
            X,
            y,
            test_size=config.TEST_SIZE,
            random_state=config.SEED,
            stratify=stratify,
        )

    if config.SPLIT == "chronologique":
        if config.TIME_COLUMN is None or config.TIME_COLUMN not in df.columns:
            raise ValueError(
                "SPLIT = 'chronologique' demande une colonne de date valide dans TIME_COLUMN "
                f"(valeur actuelle : {config.TIME_COLUMN!r})."
            )
        # Positions des lignes triées de la plus ancienne à la plus récente
        order = pd.to_datetime(df[config.TIME_COLUMN]).argsort(kind="stable").to_numpy()
        n_test = math.ceil(len(df) * config.TEST_SIZE)  # même arrondi que train_test_split
        train_idx, test_idx = order[:-n_test], order[-n_test:]
        return X.iloc[train_idx], X.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx]

    raise ValueError(
        f"SPLIT inconnu : {config.SPLIT!r}. Valeurs possibles : 'random' ou 'chronologique'."
    )