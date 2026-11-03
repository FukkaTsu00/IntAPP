# ADR 003 : transmission de la clé API et origines CORS autorisées

Date : 03/11/2026 · Auteurs : Badre El Mouden, …

## Contexte
L'API MaintAI ne doit répondre qu'aux programmes autorisés, et la clé qui les identifie ne doit apparaître ni dans le code ni dans Git. Une page web servie sur `http://localhost:5500` doit pouvoir appeler l'API depuis le navigateur ; une page servie depuis une autre origine, non.

Deux décisions sont à prendre : **où le client transmet la clé**, et **quelles origines le navigateur a le droit d'utiliser**.

## Options étudiées

### Décision 1 : où transmettre la clé
1. **Dans un en-tête `X-API-Key`** : la clé ne figure pas dans l'URL, donc pas dans les journaux du serveur, l'historique du navigateur ni l'en-tête `Referer`. Fonctionne pour toutes les méthodes (GET comme POST). FastAPI la lit avec `Header()` et `/docs` affiche un champ dédié. Inconvénient : un en-tête personnalisé déclenche une requête de pré-vérification CORS (OPTIONS), il faut l'autoriser dans `allow_headers`.
2. **Dans l'URL (`?api_key=...`)** : simple à tester dans un navigateur, mais la clé est écrite partout où l'URL est enregistrée (journaux, proxy, historique, captures d'écran, liens partagés). Une clé qui a fuité doit être changée.
3. **Dans le corps JSON** : la clé reste hors de l'URL, mais elle se mélange aux données métier : il faut l'ajouter au schéma `SensorReading` (qui refuse les champs en trop), elle n'existe pas pour une requête GET, et chaque route doit la vérifier elle-même au lieu d'une dépendance commune.

### Décision 2 : quelles origines autoriser
1. **Une liste explicite, lue dans `.env` (`MAINTAI_CORS_ORIGINS`)** : seules les pages connues peuvent appeler l'API depuis un navigateur. La liste change selon l'environnement (développement, production) sans toucher au code. Inconvénient : toute nouvelle origine demande de modifier `.env` et de relancer uvicorn.
2. **`*` (toutes les origines)** : aucune configuration, mais n'importe quel site ouvert dans le navigateur d'un utilisateur peut appeler l'API. On perd la seule protection que le navigateur apporte côté client.
3. **Une liste écrite en dur dans `main.py`** : explicite, mais il faut modifier le code et redéployer pour changer d'environnement, et la configuration de production finirait dans Git.

## Décision
- **La clé voyage dans l'en-tête `X-API-Key`.** Elle est vérifiée par `require_api_key()`, ajoutée comme dépendance du router `/v1` : chaque route `/v1` est protégée, `/health` reste public. La comparaison utilise `secrets.compare_digest` (temps constant). La clé attendue est lue dans `MAINTAI_API_KEY` (fichier `.env`, ignoré par Git ; `.env.example` commité avec une fausse valeur). Sans clé configurée, le serveur répond 500 plutôt que d'accepter tout le monde.
- **Les origines autorisées sont une liste explicite, lue dans `.env`** (`MAINTAI_CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500`), avec seulement les méthodes `GET`, `POST` et les en-têtes `Content-Type`, `X-API-Key`.

Raison principale : ce sont les deux contraintes du projet. La clé ne doit fuiter nulle part (l'URL fuit partout), et seule la page de `localhost:5500` doit fonctionner (ce que `*` rendrait impossible).

## Conséquences
- Facilité : un seul endroit protège toutes les routes `/v1` ; changer de clé ou d'origine se fait dans `.env`, sans commit.
- Ce que l'on perd avec les autres options : avec l'URL, la clé se retrouve dans les journaux et doit être changée ; avec le corps, le schéma et chaque route se compliquent ; avec `*`, n'importe quel site peut utiliser l'API depuis le navigateur d'un utilisateur.
- Limites à garder en tête :
  - CORS est appliqué **par le navigateur** seulement : `curl`, un script Python ou le client Java ne sont pas concernés. CORS ne remplace pas la clé, il la complète.
  - La clé saisie dans la page web est visible par l'utilisateur de cette page : en production, une page publique passera par un serveur intermédiaire, ou par une authentification par utilisateur (séance 8).
  - En HTTP simple, la clé circule en clair : en production, l'API sera servie en HTTPS.
  - Après chaque modification de `.env`, il faut relancer uvicorn (la configuration CORS est lue au démarrage).
  - Si `.env` est poussé par erreur : `git rm --cached .env`, commit, et **changer la clé**.
