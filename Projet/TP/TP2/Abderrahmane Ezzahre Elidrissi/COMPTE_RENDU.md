# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

**Groupe :** G2  ·  **Membres :** Abderrahmane Ezzahre Elidrissi  ·  **Date :** 03/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP2.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Activité 1 : casser son API (dans `TP/TP1`)

Vos cinq requêtes, le code que vous aviez **prévu**, puis le code **obtenu** dans `/docs` :

| Requête | Ce qui ne va pas          | Code prévu | Code obtenu |
| ------- | ------------------------- | ---------- | ----------- |
| 1       | champ manquant            | 422        | 422         |
| 2       | valeur absurde            | 422        | 422         |
| 3       | texte au lieu d'un nombre | 422        | 422         |
| 4       | champ en trop             | 422        | 422         |
| 5       | mauvaise route            | 404        | 404         |

Une de vos prévisions était-elle fausse ? Laquelle, et pourquoi ?

…

Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :

```
18 passed, 1 warning
```

À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour votre fonction, et pourquoi ?

`@pytest.mark.parametrize` sert à lancer une même fonction de test plusieurs fois, chaque exécution recevant un jeu de valeurs différent. Ici, pytest compte 5 tests, soit un par entrée de la liste `CAS_REFUSES`, ce qui donne 13 + 5 = 18.

## 2. ruff

Sortie de `ruff check .` dans `TP/TP1` :

```
All checks passed!
```

Quelle différence entre `ruff check .` et `python -m pytest` ? Que vérifie chacun ?


ruff analyse le code sans le lancer et contrôle sa propreté : imports inutilisés ou mal ordonnés, variables jamais employées. pytest, lui, exécute le code et s'assure qu'il se comporte comme prévu, grâce aux tests du dossier `tests`.

## 3. Mise en place du TP2 (dans `TP/TP2`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
==================== short test summary info =================
FAILED tests/test_security.py::test_missing_key_is_rejected - AssertionError: assert 200 == 401
FAILED tests/test_security.py::test_wrong_key_is_rejected - assert 200 == 401
============= 2 failed, 16 passed, 1 warning in 3.08s ==============
```

Quels sont les deux tests qui échouent, et que reçoivent-ils au lieu de 401 ?
Les deux tests obtiennent un 200 à la place du 401 attendu, puisque l'API ne contrôle encore aucune clé.
…

## 4. La clé API (sprint 1)

Votre fonction `require_api_key()` (`maintai/api/security.py`) :

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""

    expected_key = get_settings().api_key

    # Vérifier la configuration du serveur
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="Clé API non configurée sur le serveur."
        )

    # Vérifier la clé fournie par le client
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=401,
            detail="Clé API absente ou invalide."
        )
```

Votre ligne `router = ...` dans `maintai/api/main.py` :

```python
router = APIRouter(prefix="/v1",dependencies=[Depends(require_api_key)])
```

Après avoir écrit `security.py` seul (sans toucher au router), combien de tests échouent ? Pourquoi ?
2 tests échouent, car la fonction n'est jamais appelée : elle n'est pas encore branchée sur le router.
…

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
18 passed, 1 warning in 3.21s
```

Lancez `uvicorn maintai.api.main:app --reload --env-file .env`, puis envoyez ces requêtes (avec `/docs` ou `curl.exe`) :

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health`, sans clé |200 | {"status": "ok","model_loaded": true}|
| `POST /v1/predict`, relevé normal, sans clé |401 |{"detail": "Clé API absente ou invalide."} |
| `POST /v1/predict`, relevé normal, fausse clé | 401|{"detail": "Clé API absente ou invalide."} |
| `POST /v1/predict`, relevé normal, bonne clé | 200| {"failure_probability": 0.9553,"alert": true,"threshold": 0.3,"model_version": "2026-11-04T19:13:01Z"}|
| `POST /v1/predict`, 500 °C, sans clé |401 |{"detail": "Clé API absente ou invalide."} |
| `POST /v1/predict`, 500 °C, bonne clé |422 | {
  "detail": [{"type": "less_than_equal","loc": ["body","temperature_c"],"msg": "Input should be less than or equal to 150","input": 500,"ctx": {"le": 150}} ]}|

500 °C sans clé et 500 °C avec la clé ne donnent pas le même code. Pourquoi ?

Parce que la clé est contrôlée avant les données. Sans clé, la requête est stoppée immédiatement (401) et le corps n'est jamais examiné. Avec la bonne clé, elle franchit ce contrôle, puis la validation rejette les 500 °C, qui dépassent le maximum de 150 (422).

Relancez uvicorn **sans** `--env-file .env` et envoyez un relevé avec votre clé. Quel code obtenez-vous, et pourquoi ce n'est pas 401 ?

J'obtiens un 500 : sans `.env`, le serveur ne dispose d'aucune clé configurée. C'est donc une erreur côté serveur, et non un problème de clé envoyée par le client, d'où l'absence de 401.

## 5. La page web (sprint 2)

Votre code `fetch` (le contenu du `addEventListener` dans `web/index.html`) :

```javascript
document.getElementById("go").addEventListener("click", async () => {
  const reading = Object.fromEntries(
    FEATURES.map(f => [
      f,
      Number(document.getElementById(f).value)
    ])
  );

  const url = document.getElementById("url").value.trim();
  const cle = document.getElementById("key").value;

  try {
    const resp = await fetch(`${url}/v1/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": cle
      },
      body: JSON.stringify(reading)
    });

    const data = await resp.json();

    if (!resp.ok) {
      show("err", `Erreur HTTP ${resp.status} : ${data.detail || "Erreur inconnue"}`);
      return;
    }

    const probability = (data.failure_probability * 100).toFixed(2);

    if (data.alert) {
      show("alert", `⚠️ Alerte ! Risque de panne : ${probability}%`);
    } else {
      show("ok", `✓ Aucun risque élevé détecté. Probabilité de panne : ${probability}%`);
    }

  } catch (e) {
    show("err", `Impossible de contacter l'API : ${e.message}`);
  }
});
```

Ce qu'affiche la page (servie sur le port 5500) :

| Essai | Ce qu'affiche la page |
|---|---|
| relevé normal, bonne clé | ✓ Aucun risque élevé détecté. Probabilité de panne : 14.55%|
| 500 °C, bonne clé |Erreur HTTP 422 : [object Object]|
| relevé normal, fausse clé | Erreur HTTP 401 : Clé API absente ou invalide.|

**Expérience CORS.** Servez la page sur le port 5501. Que dit la page, et que dit la console (F12) ?

Impossible de contacter l'API : Failed to fetch
`Access to fetch at 'http://localhost:8000/v1/predict' from origin 'http://localhost:5501' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.`

Pourquoi `curl.exe` obtient-il une réponse alors que la page du port 5501 est bloquée ?

Parce que CORS est une règle que seul le navigateur applique. Le fichier `.env` n'autorise que `http://localhost:5500` et `http://127.0.0.1:5500`, si bien que le navigateur bloque la page du port 5501. curl n'est pas un navigateur : il ne contrôle pas CORS et récupère la réponse dès que la clé est correcte.

## 6. Les tests de l'activité 1 dans le TP2

Copiez `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, et avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?

5 failed, 18 passed, 1 warning

Sans `headers=HEADERS`, la clé API n'est pas transmise. `require_api_key()` bloque donc la requête et renvoie un 401 avant que Pydantic ait pu examiner le corps JSON et, le cas échéant, répondre par un 422.

Dernière ligne de `python -m pytest` avec `headers=HEADERS` :

```
======================== 23 passed, 1 warning in 0.97s =========================
```

## 7. Questions de compréhension

1. Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?
   401 Unauthorized : le client n'est pas identifié, la clé API étant absente ou erronée.

   422 Unprocessable Entity : le serveur comprend la requête, mais les données envoyées enfreignent les règles de validation définies avec Pydantic.

   403 Forbidden : le client est bien identifié, mais n'a pas le droit d'accéder à la ressource demandée.
2. Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?
   La clé API est un secret : l'écrire dans le code ou dans Git reviendrait à la rendre accessible à n'importe qui ayant accès au dépôt.
   - `.env` renferme les vraies valeurs de configuration, dont la clé secrète. Il figure dans le `.gitignore` et n'est pas commité.
   - `.env.example` présente les variables attendues avec des valeurs factices ou des indications. Il est commité afin que les autres développeurs sachent comment configurer leur environnement.
3. Pourquoi la clé voyage-t-elle dans un en-tête et pas dans l'URL ?
   Une URL peut être conservée dans l'historique du navigateur, les journaux des serveurs ou les outils de supervision. Glisser la clé dans un en-tête HTTP (`X-API-Key`) limite donc les risques de fuite accidentelle. En production, HTTPS reste en outre indispensable pour protéger la clé pendant le transport.
4. Que fait `secrets.compare_digest` de plus qu'un simple `==` ?
   `secrets.compare_digest()` compare deux chaînes en un temps qui ne dépend pas de leur contenu, alors qu'un `==` s'arrête dès le premier caractère différent. Cela protège contre les attaques par mesure du temps de réponse (*timing attacks*).
5. Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?
   Une origine se définit par la combinaison de trois éléments :
   - le protocole (HTTP ou HTTPS) ;
   - le nom d'hôte (par exemple `localhost`) ;
   - le port.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp2` existe sur GitHub : oui / non
- `git status` avant le commit : le fichier `.env` apparaissait-il ? oui / non
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 9. Ce qui reste flou

Je dois encore consolider la distinction entre les codes HTTP 401, 403 et 422, ainsi que l'ordre dans lequel FastAPI enchaîne l'authentification et la validation des données. J'aimerais aussi mieux saisir le fonctionnement de CORS, la notion d'origine et les bonnes pratiques pour protéger une clé API dans une application web.
