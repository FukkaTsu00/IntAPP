# Compte rendu · TP1 : une API de prédiction pour MaintAI

**Groupe :** G2 · **Membres :** EL MEHDI ES-SAKHI · **Date :** 27/10/2026

---

## 1. Mise en place

**Dernière ligne de `python -m pytest` après la mise en place initiale :**

```
3 failed, 10 passed
```

**Dans `tests/test_api.py`, 4 tests sur 7 passent déjà alors que rien n'est écrit. Lesquels ?**

Les quatre tests qui passent initialement sont :

- `test_health` : vérifie que l'endpoint `/health` retourne le code 200 et le statut attendu.
- `test_out_of_range_value_is_rejected` : vérifie le rejet d'une valeur hors limites.
- `test_missing_field_is_rejected` : vérifie le rejet d'un champ manquant.
- `test_openapi_documents_predict` : vérifie que la route `/v1/predict` est présente dans la documentation OpenAPI.

Les deux tests de validation passent pour une mauvaise raison : `extra="forbid"` interdit les champs supplémentaires, mais ne définit aucune borne pour les valeurs numériques. En réalité, le champ `temperature_c` à 500 n'est pas encore rejeté pour une raison physique, et le test du champ manquant passe grâce à la validation obligatoire des champs par Pydantic, et non grâce aux bornes définies avec `Field(ge=..., le=...)`.

---

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | Minimum (`ge`) | Maximum (`le`) | Justification physique |
|---|---|---:|---:|---|
| `temperature_c` | float | -40 | 150 | Couvre les températures ambiantes très basses et les températures élevées rencontrées dans un environnement moteur. |
| `vibration_mm_s` | float | 0 | 50 | Une vitesse vibratoire efficace ne peut pas être négative. Une valeur de 50 mm/s représente une vibration exceptionnellement importante. |
| `load_pct` | float | 0 | 150 | La charge ne peut pas être négative et peut dépasser temporairement la charge nominale en situation de surcharge. |
| `runtime_hours` | float | 0 | 200 000 | Le temps de fonctionnement cumulé ne peut pas être négatif. La limite supérieure couvre une durée d'utilisation industrielle importante. |

**Après avoir écrit `schemas.py` seul, que donne `python -m pytest`, et quel est le message d'erreur des tests qui échouent ? Pourquoi est-ce un bon signe ?**

3 failed, 10 passed (NotImplementedError)

Les tests qui échouent devraient signaler que les champs obligatoires ne sont pas encore présents dans la classe `SensorReading` si le code initial ne les déclarait pas. C'est un bon signe, car les tests détectent que le schéma doit être complété avant que l'API puisse fonctionner correctement.

---

## 3. La fonction `predict()` (`maintai/api/main.py`)

**Code implémenté :**

```python
@router.post("/predict", response_model=PredictionOut)
def predict(reading: SensorReading) -> PredictionOut:
    predictor = state.get("predictor")

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Modèle non chargé : lancez `python -m maintai.train`, puis redémarrez l'API.",
        )

    return PredictionOut(**predictor.predict(reading.model_dump()))
```

**Pourquoi répondre 503 et pas 500 quand le modèle manque ?**

Le code HTTP 503 signifie que le service est temporairement indisponible, car une dépendance nécessaire, ici le modèle de Machine Learning, n'est pas disponible. Le code 500 indique plutôt une erreur interne inattendue du serveur. Le code 503 décrit donc plus précisément la situation et informe le client que le service pourra redevenir opérationnel après le chargement du modèle.

**Pourquoi le modèle est-il chargé une seule fois, au démarrage, et pas à chaque requête ?**

Le chargement du modèle est une opération relativement coûteuse en temps et en ressources. Le charger une seule fois au démarrage permet de réduire la latence des requêtes, d'éviter les chargements répétitifs et de partager la même instance du modèle entre les différentes prédictions.

---

## 4. Les tests

**Dernière ligne de `python -m pytest` à la fin du TP :**

```text
19 passed, 1 warning in 2.92s
```

Les 19 tests sont réussis :

- `tests/test_api.py` : 7 tests.
- `tests/test_casser.py` : 5 tests.
- `tests/test_data.py` : 3 tests.
- `tests/test_demo.py` : 1 test.
- `tests/test_train.py` : 3 tests.

Un avertissement de dépréciation concerne l'utilisation de `httpx` avec `starlette.testclient`. Il ne bloque pas l'exécution des tests.

---

## 5. L'API en marche

**Entraînement du modèle :**

```text
{
  "model": {
    "accuracy": 0.904,
    "recall": 0.75,
    "precision": 0.622,
    "threshold": 0.3
  },
  "baseline": {
    "accuracy": 0.864,
    "recall": 0.0
  },
  "n_train": 4000,
  "n_test": 1000
}
Modèle sauvegardé dans models\model.joblib
```

**Démarrage de l'API :**

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

| Requête | Code obtenu | Réponse |
|---|---:|---|
| `GET /health` | 200 | À récupérer dans `/docs` |
| `POST /v1/predict` avec les valeurs fournies | 200 | À récupérer dans `/docs` |
| `POST /v1/predict` avec `temperature_c = 500` | 422 | Erreur de validation Pydantic |
| `POST /v1/predicte` | 404 (attendu) | Not Found |

**Dans `/docs`, où voit-on les bornes choisies ?**

Dans la documentation interactive Swagger, en ouvrant `POST /v1/predict`, puis le schéma `SensorReading`. Les propriétés affichent les limites `minimum` et `maximum`, ainsi que les descriptions définies dans Pydantic.

---

## 6. Questions de compréhension

**1. REST et FastAPI : quelle est la différence ?**

REST est un style architectural qui définit des principes pour concevoir des API utilisant notamment des ressources et des méthodes HTTP. FastAPI est un framework Python permettant de développer des API REST rapidement, avec validation automatique des données et génération de documentation OpenAPI.

**2. Le schéma Pydantic sert à trois choses. Lesquelles ?**

- Valider les données reçues et vérifier leurs types et leurs limites.
- Rejeter les données invalides avant leur traitement.
- Générer automatiquement la documentation OpenAPI/Swagger à partir des types, contraintes et descriptions.

**3. Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?**

- `localhost` désigne la machine locale sur laquelle le serveur fonctionne.
- `8000` désigne le port sur lequel Uvicorn écoute les requêtes.
- `/v1/predict` désigne le chemin de l'endpoint utilisé pour effectuer une prédiction.

**4. Pourquoi `/v1` dans l'adresse ?**

`/v1` indique la première version de l'API. Cela permet de faire évoluer l'API ultérieurement sans casser la compatibilité avec les clients qui utilisent encore l'ancienne version.

**5. Dans `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?**

`maintai.api.main` représente le chemin du module Python contenant l'API. `app` désigne l'objet FastAPI créé dans ce module et utilisé par Uvicorn pour démarrer le serveur.

---

## 7. Le rendu Git

- **Lien de la pull request :** à compléter.
- **Le tag `tp1` existe sur GitHub :** à vérifier.
- **Qui a relu la pull request et quel commentaire a-t-il laissé ?** à compléter.

---

## 8. Ce qui reste flou

La distinction entre les codes HTTP 404, 422, 500 et 503, ainsi que le fonctionnement du cycle de vie de l'application FastAPI (`lifespan`), méritent d'être approfondis. Il reste également à mieux comprendre comment les contraintes Pydantic sont automatiquement intégrées dans la documentation Swagger.
