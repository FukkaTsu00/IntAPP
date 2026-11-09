# Compte rendu · TP1 : une API de prédiction pour MaintAI

**Groupe :** G2 · **Membres :** Abderrahmane Ezzahre Elidrissi · **Date :** 27/10/2026

## 1. Mise en place

Dernière ligne de `python -m pytest` après la mise en place initiale :

```
3 failed, 10 passed
```

**Dans `tests/test_api.py`, 4 tests sur 7 passent déjà alors que rien n'est écrit. Lesquels ?**

- `test_health` : s'assure que l'endpoint `/health` renvoie bien le code 200 accompagné du statut prévu.
- `test_out_of_range_value_is_rejected` : valide le rejet d'une valeur hors gabarit.
- `test_missing_field_is_rejected` : contrôle l'élimination des charges utiles incomplètes.
- `test_openapi_documents_predict` : confirme que la route `/v1/predict` figure bien dans la documentation OpenAPI.

Les deux tests de validation fonctionnent au départ pour une raison inattendue : la configuration `extra="forbid"` bloque les arguments non déclarés mais n'impose pas de limites numériques. Concrètement, le paramètre `temperature_c` fixé à 500 n'est pas encore filtré par une logique physique, et le test sur le champ manquant réussit grâce au typage obligatoire de Pydantic plutôt qu'en raison des bornes fixées via `Field(ge=..., le=...)`.

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | Minimum (ge) | Maximum (le) | Justification physique |
| --- | --- | --- | --- | --- |
| `temperature_c` | float | -40 | 150 | Englobe aussi bien les froids ambiants extrêmes que les pics de chaleur relevés au cœur d'un moteur. |
| `vibration_mm_s` | float | 0 | 50 | Une intensité vibratoire ne peut pas descendre sous zéro. Un plafond à 50 mm/s symbolise une secousse d'une sévérité critique. |
| `load_pct` | float | 0 | 150 | L'indicateur de charge reste positif tout en tolérant un dépassement passager de la valeur nominale en cas de surrégime. |
| `runtime_hours` | float | 0 | 200 000 | Exclut d'emblée les valeurs négatives tout en prévoyant une amplitude large propre à la durée de vie opérationnelle d'une machine. |

**Après avoir écrit `schemas.py` seul, que donne `python -m pytest`, et quel est le message d'erreur des tests qui échouent ? Pourquoi est-ce un bon signe ?**

Résultat : `3 failed, 10 passed` (`NotImplementedError`).

Les tests en échec signalent logiquement que les attributs indispensables ne sont pas encore intégrés dans la classe `SensorReading` si le squelette initial les omettait. C'est un indicateur positif, car cela montre que la suite de tests repère l'absence du schéma adéquat avant que l'API ne puisse tourner convenablement.

## 3. La fonction `predict()` (`maintai/api/main.py`)

Code implémenté :

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

Le code HTTP 503 traduit une indisponibilité transitoire du service, imputable à l'absence d'une ressource critique, en l'occurrence le modèle d'apprentissage. À l'inverse, le code 500 pointe un dysfonctionnement interne inopiné. Le statut 503 s'avère donc beaucoup plus précis pour notifier l'appelant qu'un chargement préalable réglera le problème.

**Pourquoi le modèle est-il chargé une seule fois, au démarrage, et pas à chaque requête ?**

L'initialisation d'un modèle représente une tâche lourde en ressources et en temps CPU. L'exécuter une unique fois au lancement permet d'abaisser la latence des appels, de s'affranchir d'itérations redondantes et de mutualiser le même objet à travers toutes les requêtes de prédiction.

## 4. Les tests

Dernière ligne de `python -m pytest` à la fin du TP :

```
19 passed, 1 warning in 2.92s
```

Les 19 tests sont réussis :

| Fichier | Nombre de tests |
| --- | --- |
| `tests/test_api.py` | 7 |
| `tests/test_casser.py` | 5 |
| `tests/test_data.py` | 3 |
| `tests/test_demo.py` | 1 |
| `tests/test_train.py` | 3 |

Un avertissement mineur lié à la compatibilité de `httpx` avec `starlette.testclient` est mentionné, sans perturber le bon déroulement de la phase de test.

## 5. L'API en marche

**Entraînement du modèle :**

```json
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
```

Modèle sauvegardé dans `models\model.joblib`.

**Démarrage de l'API :** `Uvicorn running on http://127.0.0.1:8000` — `Application startup complete.`

| Requête | Code obtenu | Réponse |
| --- | --- | --- |
| `GET /health` | 200 | À récupérer dans `/docs` |
| `POST /v1/predict` avec les valeurs fournies | 200 | À récupérer dans `/docs` |
| `POST /v1/predict` avec `temperature_c = 500` | 422 | Erreur de validation Pydantic |
| `POST /v1/predicte` | 404 (attendu) | Not Found |

**Dans `/docs`, où voit-on les bornes choisies ?**

Au sein de l'interface interactive Swagger, en sélectionnant l'endpoint `POST /v1/predict` puis en consultant le schéma `SensorReading`. Les attributs y affichent explicitement les seuils limites et les descriptions fixées dans Pydantic.

## 6. Questions de compréhension

**REST et FastAPI : quelle est la différence ?**

REST correspond à une architecture normative régissant la construction d'interfaces web via des ressources et des verbes HTTP. FastAPI est pour sa part un framework de développement Python facilitant la création rapide d'API conformes à ces concepts, tout en automatisant la validation et l'écriture de la documentation OpenAPI.

**Le schéma Pydantic sert à trois choses. Lesquelles ?**

1. Contrôler la conformité, le formatage et le typage des charges reçues.
2. Stopper et écarter de façon anticipée les données erronées.
3. Générer automatiquement l'interface et la documentation Swagger/OpenAPI.

**Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?**

- `localhost` représente la machine hôte hébergeant le service.
- `8000` correspond au port réseau ouvert pour écouter le trafic.
- `/v1/predict` pointe vers le chemin d'accès précis sollicité pour lancer la prédiction.

**Pourquoi `/v1` dans l'adresse ?**

Ce segment indique l'itération majeure initiale de l'interface. Cela permet de faire évoluer le service à l'avenir sans compromettre la rétrocompatibilité des applications clientes existantes.

**Dans `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?**

`maintai.api.main` indique l'arborescence du module contenant l'application, tandis que `app` désigne l'instance de l'objet FastAPI instanciée dans ce fichier et pilotée par Uvicorn.

## 7. Le rendu Git

Lien de la pull request : https://github.com/FukkaTsu00/IntAPP

## 8. Ce qui reste flou

La distinction subtile entre les statuts HTTP 404, 422, 500 et 503, ainsi que la gestion interne du cycle de vie des applications FastAPI (`lifespan`), nécessitent d'être creusées. De même, le mécanisme exact par lequel Pydantic injecte les contraintes dans l'interface Swagger demeure à approfondir.
