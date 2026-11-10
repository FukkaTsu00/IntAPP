# TP1 : une API de prédiction pour MaintAI

**Groupe :** G2 · **Membre :** Othmane Ettayam · **Date :** 27/10/2026

Dépôt : https://github.com/FukkaTsu00/IntAPP (dossier `Projet/TP/TP1`, branche `main`)

---

## 1. Mise en place

Juste après la mise en place, avant d'avoir écrit la moindre ligne, `python -m pytest` se termine par :

```
3 failed, 10 passed
```

Dans `tests/test_api.py`, 4 tests sur 7 sont déjà verts alors que le code n'existe pas encore :

- `test_health`
- `test_out_of_range_value_is_rejected`
- `test_missing_field_is_rejected`
- `test_openapi_documents_predict`

**Pourquoi les deux tests « 422 » passent pour une mauvaise raison ?**

Le `model_config` de `SensorReading` contient `extra="forbid"`, ce qui interdit à Pydantic d'accepter un champ non déclaré. Comme la classe ne contient encore que `pass`, aucun champ n'est déclaré : tout ce que l'on envoie est « inconnu » et chaque requête reçoit un 422, y compris un relevé parfaitement valide.

Les deux tests obtiennent donc le 422 qu'ils attendent, mais pas pour la raison prévue. Ce n'est ni la température de 500 qui dépasse une borne, ni le champ manquant qui est détecté : le schéma refuse simplement tout. Ce qui le prouve, c'est que le test envoyant un relevé valide échoue au même moment. Retenir : un test vert ne suffit pas, il faut comprendre pourquoi il l'est.

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | `ge` | `le` | Pourquoi ces bornes (raisonnement physique, pas le min/max des données) |
|---|---|---|---|---|
| `temperature_c` | `float` | -40 | 150 | -40 °C, c'est un démarrage à froid dans un atelier non chauffé ou en extérieur. 150 °C, c'est tout près de la limite d'isolation d'un bobinage moteur (classe F : 155 °C). Plus haut, soit le capteur est en panne, soit le moteur a déjà grillé : la valeur n'a plus de sens. |
| `vibration_mm_s` | `float` | 0 | 50 | Une amplitude ne peut pas être négative. D'après l'ISO 10816, une machine entre déjà en zone dangereuse vers 7 à 11 mm/s, mais on ne refuse pas ces valeurs : c'est justement là que l'API doit lever une alerte. 50 mm/s laisse de la marge pour une machine en train de casser sans laisser passer l'absurde. |
| `load_pct` | `float` | 0 | 150 | Charge en % de la charge nominale, 0 % pour une machine à vide. Un moteur dépasse régulièrement 100 % au démarrage ou lors d'un pic de production. Plafonner à 100 refuserait des relevés réels, surtout ceux des machines surchargées. Vers 150 %, les protections thermiques coupent le moteur. |
| `runtime_hours` | `float` | 0 | 200 000 | Un compteur d'heures ne descend jamais sous 0. 200 000 h font environ 23 ans de marche continue, soit la durée de vie d'un gros moteur industriel. `float` plutôt que `int`, pour accepter par exemple 15000,5 h. |

Règle suivie : les bornes écartent les valeurs **impossibles** (capteur en panne, erreur de saisie), pas les valeurs **anormales**. Une machine en mauvais état doit passer la validation, sinon elle ne déclenchera jamais d'alerte.

**Résultat de `pytest` avec uniquement `schemas.py` écrit :**

```
3 failed, 10 passed (NotImplementedError)
```

Il reste 3 échecs, mais l'erreur a changé : ce n'est plus un 422, c'est une `NotImplementedError`. C'est bon signe : un relevé valide franchit maintenant la validation et arrive jusqu'à `predict()`, qui n'est pas encore écrite. Le schéma fait son travail, il ne manque que la fonction. Les deux tests 422 restent verts, cette fois pour la bonne raison : le relevé valide étant accepté, le refus vient bien de la borne de température ou du champ manquant.

## 3. La fonction `predict()` (`maintai/api/main.py`)

```python
@router.post("/predict", response_model=PredictionOut)
def predict(reading: SensorReading) -> PredictionOut:
    predictor = state.get("predictor")
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Modèle non chargé : lancez `python -m maintai.train`, puis redémarrez l'API.",
        )
    prediction = predictor.predict(reading.model_dump())
    return PredictionOut(**prediction)
```

**Pourquoi un 503 plutôt qu'un 500 quand le modèle est absent ?**

Un 500 (*Internal Server Error*) veut dire « quelque chose d'imprévu a planté », donc un bug que seul un développeur peut régler. Ici rien n'a planté : le serveur tourne, mais il n'a pas la ressource dont il a besoin pour prédire. C'est un cas connu et prévu. Le 503 (*Service Unavailable*) décrit exactement cette situation : indisponibilité temporaire, que l'on corrige en entraînant le modèle puis en redémarrant l'API. Cela évite aussi, côté supervision, de confondre un modèle manquant avec un vrai bug, et le message `detail` explique quoi faire.

**Pourquoi charger le modèle une seule fois, au démarrage ?**

Charger `model.joblib` coûte du temps et de la mémoire (lecture du disque, reconstruction de l'objet), alors que le modèle ne change pas tant que l'application tourne. Le `lifespan` de FastAPI le charge donc une fois au lancement et le range dans `state` : chaque requête le réutilise, et une prédiction ne coûte plus que le calcul. Autre avantage : un problème de chargement se voit tout de suite dans `/health` (`"model_loaded": false`), pas en plein trafic.

## 4. Les tests

Résultat final de `python -m pytest` :

```
13 passed in 1.43s
```

## 5. L'API en marche

| Requête | Code | Corps de la réponse |
|---|---|---|
| `GET /health` | 200 | `{"status": "ok", "model_loaded": true}` |
| `POST /v1/predict` avec `{"temperature_c": 72.5, "vibration_mm_s": 6.1, "load_pct": 85, "runtime_hours": 15000}` | 200 | `{"failure_probability": 0.9553, "alert": true, "threshold": 0.3, "model_version": "2026-10-27T18:13:54Z"}` |
| `POST /v1/predict` avec une température de 500 | 422 | `{"detail": [{"type": "less_than_equal", "loc": ["body", "temperature_c"], "msg": "Input should be less than or equal to 150", "input": 500, "ctx": {"le": 150.0}}]}` |
| `POST /v1/predicte` (faute de frappe dans l'URL) | 404 | `{"detail": "Not Found"}` |

**Où voit-on les bornes dans `/docs` ?**

À deux endroits. D'abord dans la section **Schemas**, en bas de page : en dépliant `SensorReading`, chaque champ affiche son type, sa description, son `minimum` et son `maximum`. Ensuite sur la route `POST /v1/predict`, dans le corps de la requête, onglet **Schema** (à côté de **Example Value**). Tout cela est généré à partir des `Field(ge=..., le=..., description=...)` du schéma.

## 6. Questions de compréhension

**1. REST et FastAPI, quelle différence ?**
REST est une façon de concevoir une API web : des URL qui désignent des ressources, des méthodes HTTP (GET pour lire, POST pour envoyer), des codes de statut précis, du JSON en entrée et en sortie, une version dans l'adresse. FastAPI est une bibliothèque Python qui permet de construire une API qui respecte ces principes, avec validation automatique et documentation OpenAPI. REST décrit comment concevoir, FastAPI fournit l'outil pour le faire.

**2. À quoi sert le schéma Pydantic ?**
À trois choses :
- **Valider.** FastAPI contrôle chaque requête avant d'appeler la fonction (types, bornes `ge`/`le`, champs obligatoires). Une valeur impossible est refusée par un 422 qui indique où et pourquoi, sans jamais solliciter le modèle.
- **Documenter.** La page `/docs` est construite à partir du schéma : champs, types, bornes, descriptions, exemple.
- **Fournir un objet typé.** Dans la fonction, `reading` n'est pas un texte JSON à découper mais un objet : `reading.temperature_c` est un `float` déjà vérifié, et `reading.model_dump()` donne le dictionnaire attendu par le modèle.

Les trois viennent de la même source, donc ils ne peuvent pas se contredire.

**3. Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?**
- `localhost` : la machine elle-même (le serveur tourne sur mon PC).
- `8000` : le port sur lequel uvicorn écoute.
- `/v1/predict` : la route, un chemin défini dans le code Python (pas un dossier du disque). `/v1` indique la version de l'API.

**4. Pourquoi `/v1` dans l'adresse ?**
Pour versionner le contrat de l'API. Si le format d'entrée ou de sortie change un jour d'une façon qui casserait les clients (champ renommé, nouvelle variable obligatoire), on publie une `/v2` à côté. Les clients existants (tableau de bord, application mobile, système d'atelier) continuent de marcher sur `/v1` et migrent à leur rythme.

**5. Dans `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?**
- `maintai.api.main` : le fichier `maintai/api/main.py`, écrit en notation de module Python (points à la place des `/`, sans `.py`).
- `app` : la variable de ce fichier qui contient l'application, créée avec `app = FastAPI(...)`. C'est cet objet qu'uvicorn exécute.

## 7. Rendu Git

- Dépôt : https://github.com/FukkaTsu00/IntAPP
- Poussé directement sur `main`, dans `Projet/TP/TP1` (ni pull request ni tag pour ce TP).
- Relecture : aucune pour l'instant.

## 8. Ce qui reste flou pour moi

- **Le choix des bornes.** La limite entre une valeur « impossible » (à refuser avec un 422) et une valeur « anormale » (que le modèle doit recevoir pour déclencher une alerte) n'est pas toujours nette. Elle dépend du type de machine, et je me demande s'il faudrait des bornes différentes selon les équipements.
- **503 ou refus de démarrer quand le modèle manque.** Avec un 503, l'API reste joignable et `/health` aide à diagnostiquer, mais elle peut tourner longtemps sans rien servir si personne ne la surveille. En refusant de démarrer, l'erreur saute aux yeux tout de suite, mais on ne peut plus interroger le service du tout. Je ne sais pas laquelle des deux est la pratique courante en production.
