# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

**Groupe :** G2  ·  **Membre :** Othmane Ettayam  ·  **Date :** 03/11/2026

---

## 1. Activité 1 : mettre son API à l'épreuve (dans `TP/TP1`)

Pour chacune de mes cinq requêtes, j'ai noté le code que j'attendais, puis celui renvoyé par `/docs` :

| Requête | Problème introduit | Code prévu | Code obtenu |
| ------- | ------------------------- | ---------- | ----------- |
| 1 | champ manquant | 422 | 422 |
| 2 | valeur absurde | 422 | 422 |
| 3 | texte à la place d'un nombre | 422 | 422 |
| 4 | champ en trop | 422 | 422 |
| 5 | mauvaise route | 404 | 404 |

**Une de mes prévisions était-elle fausse ?**

Non, les cinq codes obtenus correspondent à ce que j'avais prévu.

**Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :**

```
18 passed, 1 warning
```

**À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour ma fonction, et pourquoi ?**

Ce décorateur permet de lancer une même fonction de test plusieurs fois, chaque fois avec des valeurs différentes. Ici, pytest génère 5 tests à partir de ma fonction, soit un par ligne de la liste `CAS_REFUSES`. Le total est donc de 13 + 5 = 18.

## 2. ruff

**Sortie de `ruff check .` dans `TP/TP1` :**

```
All checks passed!
```

**Quelle différence entre `ruff check .` et `python -m pytest` ?**

`ruff` analyse le code sans l'exécuter : il contrôle sa qualité (imports inutilisés, imports mal ordonnés, variables non utilisées). `pytest`, lui, exécute réellement le code et vérifie qu'il se comporte comme prévu grâce aux tests du dossier `tests`.

## 3. Mise en place du TP2 (dans `TP/TP2`)

**Dernière ligne de `python -m pytest` juste après la mise en place :**

```
==================== short test summary info =================
FAILED tests/test_security.py::test_missing_key_is_rejected - AssertionError: assert 200 == 401
FAILED tests/test_security.py::test_wrong_key_is_rejected - assert 200 == 401
============= 2 failed, 16 passed, 1 warning in 3.08s ==============
```

**Quels tests échouent, et que reçoivent-ils à la place de 401 ?**

Il s'agit de `test_missing_key_is_rejected` et `test_wrong_key_is_rejected`. Tous deux reçoivent un 200, puisque l'API ne contrôle encore aucune clé à ce stade.

## 4. La clé API (sprint 1)

**Ma fonction `require_api_key()` (`maintai/api/security.py`) :**

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

**Ma ligne `router = ...` dans `maintai/api/main.py` :**

```python
router = APIRouter(prefix="/v1",dependencies=[Depends(require_api_key)])
```

**Après avoir écrit seulement `security.py` (sans modifier le router), combien de tests échouent, et pourquoi ?**

Deux tests échouent encore, car la fonction est définie mais jamais appelée : tant qu'elle n'est pas branchée sur le router, aucune requête ne passe par elle.

**Dernière ligne de `python -m pytest` à la fin du sprint 1 :**

```
18 passed, 1 warning in 3.21s
```

**Essais avec `uvicorn maintai.api.main:app --reload --env-file .env` :**

| Requête | Code obtenu | Corps de la réponse (JSON) |
|---|---|---|
| `GET /health`, sans clé | 200 | `{"status": "ok","model_loaded": true}` |
| `POST /v1/predict`, relevé normal, sans clé | 401 | `{"detail": "Clé API absente ou invalide."}` |
| `POST /v1/predict`, relevé normal, fausse clé | 401 | `{"detail": "Clé API absente ou invalide."}` |
| `POST /v1/predict`, relevé normal, bonne clé | 200 | `{"failure_probability": 0.9553,"alert": true,"threshold": 0.3,"model_version": "2026-11-04T19:13:01Z"}` |
| `POST /v1/predict`, 500 °C, sans clé | 401 | `{"detail": "Clé API absente ou invalide."}` |
| `POST /v1/predict`, 500 °C, bonne clé | 422 | `{"detail": [{"type": "less_than_equal","loc": ["body","temperature_c"],"msg": "Input should be less than or equal to 150","input": 500,"ctx": {"le": 150}}]}` |

**Pourquoi 500 °C donne-t-il des codes différents avec et sans clé ?**

Parce que la clé est contrôlée avant les données. Sans clé, la requête est stoppée immédiatement par un 401 et son contenu n'est jamais examiné. Avec la bonne clé, elle franchit ce contrôle, puis la validation rejette la valeur 500 °C qui dépasse le maximum autorisé de 150 (code 422).

**Relance d'uvicorn sans `--env-file .env`, avec un relevé et ma clé : quel code, et pourquoi pas 401 ?**

J'obtiens un 500. Le serveur démarre sans `.env`, donc il n'a aucune clé de référence : c'est une erreur de configuration côté serveur, pas une erreur d'authentification du client.

## 5. La page web (sprint 2)

**Mon code `fetch` (contenu du `addEventListener` dans `web/index.html`) :**

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

**Affichage de la page (servie sur le port 5500) :**

| Essai | Message affiché |
|---|---|
| relevé normal, bonne clé | ✓ Aucun risque élevé détecté. Probabilité de panne : 14.55% |
| 500 °C, bonne clé | Erreur HTTP 422 : [object Object] |
| relevé normal, fausse clé | Erreur HTTP 401 : Clé API absente ou invalide. |

**Expérience CORS : page servie sur le port 5501.**

La page affiche :

> Impossible de contacter l'API : Failed to fetch

La console (F12) indique :

> Access to fetch at 'http://localhost:8000/v1/predict' from origin 'http://localhost:5501' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.

**Pourquoi `curl.exe` reçoit-il une réponse alors que la page du port 5501 est bloquée ?**

CORS est une règle que seul le navigateur applique. Dans `.env`, seules les origines `http://localhost:5500` et `http://127.0.0.1:5500` sont autorisées : le navigateur bloque donc la page du port 5501. `curl` n'étant pas un navigateur, il ne vérifie pas CORS et obtient sa réponse dès lors que la clé est correcte.

## 6. Les tests de l'activité 1 dans le TP2

**J'ai copié `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?**

Résultat : `5 failed, 18 passed, 1 warning`.

Sans `headers=HEADERS`, la clé n'est pas envoyée. `require_api_key()` bloque donc chaque requête avec un 401, avant que Pydantic n'ait la possibilité de contrôler le corps JSON et de renvoyer un 422.

**Dernière ligne de `python -m pytest` avec `headers=HEADERS` :**

```
======================== 23 passed, 1 warning in 0.97s =========================
```

## 7. Questions de compréhension

**1. Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?**

- **401 Unauthorized** : le client n'est pas identifié, car la clé API est absente ou incorrecte.
- **422 Unprocessable Entity** : la requête est bien comprise, mais les données envoyées ne respectent pas les règles de validation Pydantic.
- **403 Forbidden** : le client est bien identifié, mais n'a pas le droit d'accéder à la ressource demandée.

**2. Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?**

La clé API est une donnée confidentielle : l'inscrire dans le code ou dans Git l'exposerait à toute personne ayant accès au dépôt.

- `.env` contient les vraies valeurs de configuration, dont la clé secrète. Il figure dans `.gitignore` et n'est **pas** commité.
- `.env.example` contient un modèle des variables attendues, avec des valeurs fictives ou des indications. C'est lui qui est commité, afin que les autres développeurs sachent comment configurer leur environnement.

**3. Pourquoi la clé voyage-t-elle dans un en-tête et non dans l'URL ?**

Une URL peut être conservée dans l'historique du navigateur, dans les journaux des serveurs ou dans des outils de supervision. Placer la clé dans un en-tête HTTP (`X-API-Key`) limite le risque de fuite accidentelle. En production, HTTPS reste indispensable pour protéger la clé pendant son transport.

**4. Que fait `secrets.compare_digest` de plus qu'un simple `==` ?**

Cette fonction compare deux chaînes en gardant un temps d'exécution indépendant de leur contenu. Elle réduit ainsi le risque d'attaques par mesure du temps de réponse (*timing attacks*), ce que ne fait pas l'opérateur `==`.

**5. Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?**

Une origine est définie par trois éléments :

- le protocole (HTTP ou HTTPS) ;
- le nom d'hôte (par exemple `localhost`) ;
- le port.

Les deux adresses ne partagent pas le même port (5500 et 8000) : ce sont donc deux origines différentes, ce qui explique pourquoi la configuration CORS est nécessaire.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp2` existe sur GitHub : oui / non
- `git status` avant le commit : le fichier `.env` apparaissait-il ? oui / non
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 9. Ce qui reste flou

- La différence entre les codes HTTP 401, 403 et 422.
- L'ordre d'exécution entre l'authentification et la validation des données dans FastAPI.
- Le fonctionnement de CORS et la notion d'origine.
- La protection des clés API dans une application web.
