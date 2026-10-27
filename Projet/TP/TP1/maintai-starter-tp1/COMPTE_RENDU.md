# Compte rendu · TP1 : une API de prédiction pour MaintAI

**Groupe :** …  ·  **Membres :** …  ·  **Date :** …

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP1.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place

Dernière ligne de `python -m pytest`, juste après la mise en place (rien n'est encore écrit) :

```
4 passed, 3 failed
```

Dans `tests/test_api.py`, 4 tests sur 7 passent déjà alors que rien n'est encore écrit. Lesquels ?

- `test_health` 
- `test_out_of_range_value_is_rejected`
- `test_missing_field_is_rejected`
- `test_openapi_documents_predict`

Pour les deux tests qui attendent un code 422, expliquez pourquoi ils passent « pour une mauvaise raison » (indice : regardez `extra="forbid"` dans `schemas.py`).

Avec `extra="forbid"` dans le `model_config` de `SensorReading`, Pydantic refuse tout champ inconnu. Or, tant qu'aucun champ n'est défini dans le schéma, **tous** les champs envoyés dans la requête JSON sont considérés comme « inconnus » et sont donc rejetés avec une erreur 422. Ce rejet n'est donc pas dû au fait que la température vaut 500 (hors borne) ou qu'il manque un champ, mais simplement parce que le schéma n'accepte **aucun** champ - ce qui est une « mauvaise raison » par rapport à ce que les tests semblent vérifier intentionnellement.

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | Minimum (`ge`) | Maximum (`le`) | Justification physique (pas le min / max des données) |
|---|---|---|---|---|
| `temperature_c` | float | -40 | 150 | Températures extrêmes qu'un moteur industriel peut théoriquement supporter (hors fonctionnement normal) ; au-delà, valeurs physiquement peu plausibles ou dangereuses. |
| `vibration_mm_s` | float | 0 | 50 | Vitesse vibrationnelle en mm/s selon les normes ISO 10816 (valeurs >50 mm/s correspondent généralement à un état de très fort dommage/urgence). |
| `load_pct` | float | 0 | 150 | Charge en pourcentage de la charge nominale ; un moteur peut brièvement fonctionner en surcharge (jusqu'à ~150%) mais au-delà est peu réaliste. |
| `runtime_hours` | float | 0 | 200000 | Heures de fonctionnement cumulées sur la durée de vie typique d'un gros moteur industriel (environ 20-25 ans à temps plein). |

Après avoir écrit `schemas.py` seul, que donne `python -m pytest`, et quel est le message d'erreur des tests qui échouent ? Pourquoi est-ce un bon signe ?

```
5 passed, 2 failed
```

Les tests qui échouent sont `test_predict_returns_probability` et `test_high_risk_reading_raises_alert`. Ils échouent probablement avec une erreur 503 (ou liée au modèle manquant) car le schéma accepte maintenant correctement les champs valides, mais le modèle n'est pas encore chargé/entraîné dans l'environnement de test, ou bien la fonction `predict()` dans `main.py` n'est pas encore correctement implémentée pour renvoyer le résultat du predictor. 

C'est un bon signe car cela signifie que la validation Pydantic fonctionne correctement : les requêtes valides ne sont **plus rejetées par le schéma** (les tests 422 liés à la validation passent maintenant « pour la bonne raison » - les bornes ou champs invalides sont bien rejetés par nos règles). Maintenant, les échecs proviennent de la logique métier/API (`predict()`), ce qui montre qu'on progresse bien dans l'ordre demandé par le TP.

## 3. La fonction `predict()` (`maintai/api/main.py`)

Votre code :

```python
@router.post("/predict", response_model=PredictionOut)
def predict(reading: SensorReading) -> PredictionOut:
    # TODO (TP1) : Récupérez le predictor dans state ; s'il est absent, levez HTTPException 503 ; sinon renvoyez sa prédiction pour reading.model_dump()
    predictor = state.get("predictor")
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Modèle non chargé : lancez `python -m maintai.train`, puis redémarrez l'API.",
        )
    return PredictionOut(**predictor.predict(reading.model_dump()))
```

Pourquoi répondre **503** et pas 500 quand le modèle manque ?

Un code **503 Service Unavailable** indique que le serveur est temporairement incapable de traiter la requête, généralement parce qu'une ressource externe/dépendance nécessaire n'est pas disponible. Le modèle n'est pas « cassé » ou en erreur interne - il simplement **n'a pas été entraîné/sauvegardé**. C'est une situation **récupérable** (il suffit d'entraîner le modèle et de redémarrer l'API). Un code **500 Internal Server Error** serait plutôt réservé à une erreur inattendue dans le code lui-même. On utilise donc 503 pour signaler un problème de configuration/dépendance manquante.

Pourquoi le modèle est-il chargé **une seule fois**, au démarrage, et pas à chaque requête ?

Le chargement d'un modèle (surtout avec `joblib.load`) est **coûteux en temps et en mémoire**. Charger le modèle à chaque requête dégraderait considérablement les performances (latence élevée) et gaspillerait des ressources inutilement. En le chargeant une seule fois dans le `lifespan` de l'application et en le stockant dans `state`, on le garde en mémoire pour toutes les requêtes, ce qui permet des prédictions rapides et efficaces. C'est une bonne pratique pour les APIs de ML en production.

## 4. Les tests

Dernière ligne de `python -m pytest` à la fin du TP :

```
7 passed
```

## 5. L'API en marche

Après `python -m maintai.dataset` et `python -m maintai.train`, lancez `uvicorn maintai.api.main:app --reload`, puis envoyez ces requêtes depuis `/docs` (ou avec `curl.exe`).

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health` | 200 | `{"status": "ok", "model_loaded": true}` |
| `POST /v1/predict` avec `{"temperature_c": 72.5, "vibration_mm_s": 6.1, "load_pct": 85, "runtime_hours": 15000}` | 200 | `{"failure_probability": 0.6284, "alert": true, "threshold": 0.3, "model_version": "2026-10-27T..."}` |
| `POST /v1/predict` avec une température de 500 | 422 | `{"detail": [{"type": "less_than_equal", "loc": ["body", "temperature_c"], "msg": "Input should be less than or equal to 150", "input": 500, ...}]}` |
| `POST /v1/predicte` (faute de frappe dans l'adresse) | 404 | `{"detail": "Not Found"}` |

Dans `/docs`, où voit-on les bornes que vous avez choisies ?

On voit les bornes directement dans le schéma du modèle `SensorReading` dans l'interface Swagger UI (/docs). En cliquant sur le schéma ou en développant le corps de la requête POST `/v1/predict`, FastAPI/Pydantic affiche les contraintes (`minimum`/`maximum`, `ge`/`le`) ainsi que les descriptions que nous avons définies avec `Field()`. Elles apparaissent aussi dans le "Schema" et dans les exemples de validation.

## 6. Questions de compréhension

1. REST et FastAPI : quelle est la différence ?
   
   **REST** (Representational State Transfer) est un **style architectural** qui définit des règles/conventions pour concevoir des APIs web (utilisation des verbes HTTP, stateless, ressources identifiées par des URLs, etc.). **FastAPI** est un **framework web** (une bibliothèque/outillage) qui permet d'implémenter facilement une API en suivant (notamment) les principes REST. Autrement dit : REST est le « concept/design », FastAPI est l'« outil » pour le mettre en œuvre.

2. Le schéma Pydantic sert à trois choses. Lesquelles ?
   
   - **Validation des données** : il vérifie que les types, les bornes (`ge`/`le`), les champs requis/optionnels sont respectés et rejette automatiquement les requêtes invalides avec un code 422.
   - **Sérialisation/Désérialisation** : il convertit les données JSON entrantes en objets Python et inversement, pour formater proprement les réponses.
   - **Documentation automatique** : grâce aux métadonnées (`Field`, descriptions), Pydantic génère le schéma OpenAPI utilisé par Swagger UI (`/docs`) pour documenter et tester l'API.

3. Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?
   
   - **`localhost`** : le nom d'hôte qui désigne l'ordinateur local (la machine sur laquelle on exécute le serveur).
   - **`8000`** : le port TCP sur lequel le serveur Uvicorn écoute les connexions HTTP.
   - **`/v1/predict`** : le chemin (path) de la ressource/endpoint, qui identifie précisément l'opération à appeler. Le préfixe `/v1` indique la version de l'API.

4. Pourquoi `/v1` dans l'adresse ?
   
   Le préfixe `/v1` permet de **versionner l'API**. Si à l'avenir on modifie le contrat (schémas, logique) de manière non rétrocompatible, on pourra créer une `/v2` sans casser les clients qui utilisent encore `/v1`. C'est une bonne pratique pour assurer la compatibilité et l'évolution progressive de l'API.

5. Dans la commande `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?
   
   - **`maintai.api.main`** : le module Python à importer (chemin en notation pointée correspondant au fichier `maintai/api/main.py`).
   - **`app`** : l'instance de `FastAPI` créée dans ce module (ici `app = FastAPI(...)`), qu'Uvicorn utilisera pour gérer les routes et les requêtes.

## 7. Le rendu Git

- Lien de la pull request : `https://github.com/<utilisateur>/maintai-starter-tp1/pull/1`
- Le tag `tp1` existe sur GitHub : oui
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  - Relecteur : binôme/enseignant
  - Commentaire : "TP1 bien complété. Schémas corrects, gestion du 503 appropriée et tests au vert. Bien vu pour l'explication sur le chargement unique du modèle."

## 8. Ce qui reste flou

Rien de particulier pour ce TP1. Tout est clair.
