# Compte rendu · TP1 : une API de prédiction pour MaintAI

**Groupe :** G2  ·  **Membres :** Alaaeddine Bakkar  ·  **Date :** 27/10/2026

---

## 1. Mise en place

Dernière ligne de `python -m pytest`, juste après la mise en place (rien n'est encore écrit) :

```
3 failed, 10 passed
```

Dans `tests/test_api.py`, 4 tests sur 7 passent déjà alors que rien n'est écrit. Lesquels ?

- `test_health`
- `test_out_of_range_value_is_rejected`
- `test_missing_field_is_rejected`
- `test_openapi_documents_predict`

Pour les deux tests qui attendent un code 422, expliquez pourquoi ils passent « pour une mauvaise raison ».

Le `model_config` de `SensorReading` contient `extra="forbid"` : Pydantic refuse tout champ qui n'est pas déclaré dans le schéma. Or, tant qu'aucun champ n'est défini (`pass`), tous les champs envoyés dans le JSON sont « inconnus », et toute requête est rejetée avec un 422, même un relevé parfaitement valide.

`test_out_of_range_value_is_rejected` et `test_missing_field_is_rejected` reçoivent donc bien le 422 attendu, mais pas parce que la température de 500 dépasse une borne ou parce qu'un champ manque : simplement parce que le schéma refuse tout. La preuve : au même moment, le test qui envoie un relevé valide échoue lui aussi. Un test vert ne suffit pas, il faut savoir pourquoi il passe.

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | Minimum (`ge`) | Maximum (`le`) | Justification physique (pas le min / max des données) |
|---|---|---|---|---|
| `temperature_c` | `float` | -40 | 150 | -40 °C correspond à un démarrage à froid dans un atelier non chauffé ou en extérieur. 150 °C est proche de la limite d'isolation du bobinage d'un moteur industriel (classe F : 155 °C). Au-delà, le capteur est défaillant ou le moteur a déjà brûlé : la valeur n'a plus de sens physique. |
| `vibration_mm_s` | `float` | 0 | 50 | C'est une amplitude, donc jamais négative. Selon l'ISO 10816, une machine est déjà en zone dangereuse vers 7 à 11 mm/s. On ne refuse pas pour autant ces valeurs : une forte vibration est justement le cas où l'API doit lever une alerte. 50 mm/s laisse de la marge pour une machine en train de casser, sans accepter une valeur absurde. |
| `load_pct` | `float` | 0 | 150 | Charge en % de la charge nominale : 0 % pour une machine à vide. Un moteur fonctionne régulièrement au-delà de 100 % pendant un démarrage ou un pic de production. Borner à 100 refuserait des relevés réels, et précisément ceux d'une machine surchargée. Au-delà d'environ 150 %, les protections thermiques déclenchent et le moteur s'arrête. |
| `runtime_hours` | `float` | 0 | 200 000 | Un compteur d'heures n'est jamais négatif. 200 000 h représentent environ 23 ans de fonctionnement continu, la durée de vie d'un gros moteur industriel. Le type est `float` et non `int` pour accepter 15000,5 h. |

Les bornes servent à refuser les valeurs **impossibles** (capteur en panne, erreur de saisie), pas les valeurs **anormales** : une machine en mauvais état doit être acceptée par l'API, sinon elle ne reçoit jamais d'alerte.

Après avoir écrit `schemas.py` seul, que donne `python -m pytest`, et quel est le message d'erreur des tests qui échouent ? Pourquoi est-ce un bon signe ?

```
3 failed, 10 passed (NotImplementedError)

```

Il reste 3 échecs, mais l'erreur n'est plus un 422 : c'est une `NotImplementedError`. C'est un bon signe. Un relevé valide passe désormais la validation et arrive jusqu'à `predict()`, qui n'est pas encore écrite : le schéma fait son travail, seule la fonction manque. Les deux tests 422 restent verts, mais cette fois pour la bonne raison : puisqu'un relevé valide est accepté, le refus vient bien de la borne de température ou du champ manquant.

## 3. La fonction `predict()` (`maintai/api/main.py`)

Votre code :

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

Pourquoi répondre **503** et pas 500 quand le modèle manque ?

Un 500 (*Internal Server Error*) signale une erreur inattendue dans le code, un bug que seul un développeur peut corriger. L'absence du modèle n'est pas un bug : c'est un état connu et prévu, où le serveur tourne mais n'est pas encore prêt à prédire, faute d'une ressource essentielle. Le 503 (*Service Unavailable*) dit exactement cela : le problème est temporaire et récupérable, il suffit d'entraîner le modèle et de redémarrer l'API. Distinguer les deux codes évite aussi de confondre, dans la supervision, un modèle manquant avec un vrai bug. Le message `detail` indique en plus quoi faire.

Pourquoi le modèle est-il chargé **une seule fois**, au démarrage, et pas à chaque requête ?

Le chargement du modèle est coûteux en temps et en mémoire : il faut lire le fichier `model.joblib` sur le disque et reconstruire l'objet. Or le modèle ne change pas tant que l'application tourne. Le `lifespan` de FastAPI le charge donc une seule fois au démarrage et le stocke dans `state` : chaque requête le réutilise sans relire le fichier, et une prédiction ne coûte que le calcul. Un problème de chargement est en plus visible dès le démarrage, dans `/health` (`"model_loaded": false`), et non au milieu du trafic.

## 4. Les tests

Dernière ligne de `python -m pytest` à la fin du TP :

```
13 passed in 1.43s

```

## 5. L'API en marche

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health` | 200 | `{"status": "ok", "model_loaded": true}` |
| `POST /v1/predict` avec `{"temperature_c": 72.5, "vibration_mm_s": 6.1, "load_pct": 85, "runtime_hours": 15000}` | 200 | `{"failure_probability": 0.9553, "alert": true, "threshold": 0.3, "model_version": "2026-10-27T18:13:54Z"}` |
| `POST /v1/predict` avec une température de 500 | 422 | `{"detail": [{"type": "less_than_equal", "loc": ["body", "temperature_c"], "msg": "Input should be less than or equal to 150", "input": 500, "ctx": {"le": 150.0}}]}` |
| `POST /v1/predicte` (faute de frappe dans l'adresse) | 404 | `{"detail": "Not Found"}` |

Dans `/docs`, où voit-on les bornes que vous avez choisies ?

À deux endroits. Dans la section **Schemas**, en bas de la page : en dépliant `SensorReading`, chaque champ affiche son type, sa description, son `minimum` et son `maximum`. Et sur la route `POST /v1/predict`, dans l'onglet **Schema** du corps de la requête (*Request body*), à côté de l'onglet **Example Value**. Ces informations viennent directement des `Field(ge=..., le=..., description=...)` du schéma.

## 6. Questions de compréhension

1. **REST et FastAPI : quelle est la différence ?**
   REST est un style d'architecture pour concevoir des API web : des URL claires qui désignent des ressources, les méthodes HTTP (GET lit, POST envoie des données), des codes de statut précis, du JSON en entrée et en sortie, une version dans l'adresse. FastAPI est une bibliothèque Python qui permet d'écrire une API suivant ces règles, avec validation automatique et documentation OpenAPI générée. REST est la façon de concevoir, FastAPI est l'outil qui la met en œuvre.

2. **Le schéma Pydantic sert à trois choses. Lesquelles ?**
   - **Valider** : FastAPI vérifie chaque requête avant d'appeler la fonction (types, bornes `ge`/`le`, champs obligatoires). Une valeur impossible est refusée avec un 422 qui dit où et pourquoi, et le modèle n'est jamais appelé.
   - **Documenter** : FastAPI s'appuie sur le schéma pour construire la page `/docs`, avec chaque champ, son type, ses bornes, sa description et un exemple.
   - **Donner un objet Python typé** : dans la fonction, `reading` n'est pas un texte JSON à découper mais un objet. `reading.temperature_c` est un `float` déjà vérifié, et `reading.model_dump()` le transforme en dictionnaire, la forme attendue par le modèle.

   Les trois viennent du même schéma : ils ne peuvent pas se contredire.

3. **Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?**
   - `localhost` : la machine elle-même, le serveur tourne sur notre PC.
   - `8000` : le port, la « porte » sur laquelle uvicorn écoute.
   - `/v1/predict` : la route, un chemin défini dans le code Python et non un dossier sur le disque. `/v1` est la version de l'API.

4. **Pourquoi `/v1` dans l'adresse ?**
   Pour versionner le contrat de l'API. Si on modifie un jour le format d'entrée ou de sortie d'une façon qui casserait les clients (renommer un champ, ajouter une variable obligatoire), on publie une `/v2` à côté. Les clients existants (tableau de bord, application mobile, système de l'atelier) continuent de fonctionner sur `/v1` et migrent à leur rythme.

5. **Dans la commande `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?**
   - `maintai.api.main` : le fichier `maintai/api/main.py`, écrit en notation de module Python (des points à la place des `/`, sans `.py`).
   - `app` : la variable de ce fichier qui contient l'application, créée par `app = FastAPI(...)`. C'est elle qu'uvicorn fait tourner.

## 7. Le rendu Git

- Lien de la pull request : [À COMPLÉTER : https://github.com/compte/depot/pull/numéro]
- Le tag `tp1` existe sur GitHub : [À COMPLÉTER : oui, après `git push --tags`]
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  [À COMPLÉTER : nom du relecteur et son commentaire réel]

## 8. Ce qui reste flou

Le choix des bornes : la frontière entre une valeur « impossible », à refuser avec un 422, et une valeur « anormale », que le modèle doit recevoir pour lever une alerte, n'est pas toujours nette. Elle dépend du type de machine, et je ne sais pas s'il vaudrait mieux des bornes différentes selon les équipements.

Le choix entre répondre 503 et refuser de démarrer quand le modèle manque. Avec le 503, l'API reste joignable et `/health` aide au diagnostic, mais elle peut tourner longtemps sans servir à rien si personne ne surveille. Refuser de démarrer rend l'erreur visible tout de suite, mais on perd tout moyen d'interroger le service. Je ne sais pas encore laquelle de ces deux options est la pratique habituelle en production.
