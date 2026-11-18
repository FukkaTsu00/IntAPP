# Compte rendu · TP5 : suivre les entraînements (MLflow) et versionner les données (DVC)

**Groupe :** [Votre groupe] · **Membres :** EL MEHDI ES_SAKHI · **Date :** 17/11/2026-18:14

---

## 1. Mise en place (dans `TP/TP5`)

Dernière ligne de `python -m pytest` après `pip install -r requirements.txt` et `pip install -e .` :

```text
========================================= 5 failed, 27 passed, 2 warnings in 33.69s =========================================
```

Quels tests échouent, et pourquoi ?

Les tests qui échouaient concernaient la partie tracking MLflow. Ils vérifiaient notamment l'enregistrement des runs, des métriques, de la version des données et du modèle. Ces fonctionnalités n'étaient pas encore implémentées dans `log_run()` au début du TP.

Avant `pip install -e .`, où pointait le package `maintai` installé dans l'environnement ? Et après ?

Avant l'installation éditable, l'environnement réutilisait le package du TP4. Après `pip install -e .`, le package pointait vers le code source du TP5.

## 2. Sprint 1 : MLflow

Votre fonction `log_run` (`maintai/tracking.py`) :

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""

    # 1. Choisir l'expérience
    mlflow.set_experiment(EXPERIMENT)

    # 2. Ouvrir un run
    with mlflow.start_run() as run:

        # 3. Enregistrer les paramètres
        mlflow.log_params(params)

        # Enregistrer l'empreinte MD5 du fichier de données
        mlflow.log_param("data_md5", file_md5(data_path))

        # Enregistrer les métriques
        mlflow.log_metrics(metrics)

        # Enregistrer le modèle
        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_example,
            skops_trusted_types=TRUSTED_TYPES
        )

    # 4. Retourner l'identifiant du run
    return run.info.run_id

```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```text
32 passed
```

Vos runs (au moins quatre), relevés dans `mlflow ui` :

| Commande | recall | precision | accuracy |
|---|---:|---:|---:|
| `python -m maintai.train` | 0.750 | 0.622 | 0.904 |
| `python -m maintai.train --C 0.01` | 0.691 | 0.653 | 0.908 |
| `python -m maintai.train --threshold 0.2` | 0.838 | 0.543 | 0.882 |
| `python -m maintai.train --model forest` | 0.728 | 0.562 | 0.886 |
| `python -m maintai.train --threshold 0.2` sur v2 | 0.824 | 0.567 | 0.897 |

Quel run choisiriez-vous pour MaintAI, et pourquoi ?

Je choisirais la régression logistique avec un seuil de classification de 0.2. Ce run obtient le meilleur recall parmi les quatre premiers essais, avec une valeur de 0.838. Cela signifie qu'il détecte une plus grande proportion des pannes réelles. Ce choix est adapté à MaintAI car une panne manquée coûte plus cher qu'une fausse alerte. En revanche, sa précision est plus faible (0.543), ce qui signifie qu'il génère davantage de fausses alertes.

Dans `mlflow ui`, ouvrez le modèle d'un run. Quelle version de scikit-learn est indiquée dans son `requirements.txt` ? Quel problème du TP4 cela règle-t-il ?

La version exacte de scikit-learn doit être relevée dans le `requirements.txt` du modèle enregistré dans MLflow.

Cela règle le problème de reproductibilité rencontré au TP4 : le fichier du modèle seul ne suffisait pas à garantir son rechargement avec un environnement compatible. MLflow conserve également les dépendances nécessaires.

Où MLflow enregistre-t-il les runs sur votre disque ? Ces fichiers vont-ils dans Git ? Pourquoi ?

MLflow enregistre les informations des runs dans `mlflow.db` et les artefacts dans le dossier `mlruns/`.

Ces fichiers ne doivent pas être versionnés dans Git, car ils contiennent les résultats des expériences et les artefacts des modèles. Git sert principalement à versionner le code source et les fichiers de configuration du projet.

## 3. Sprint 2 : DVC

Contenu de `data/sensors.csv.dvc` pour v2 :

```yaml
outs:
- md5: 93fdeef2cac1893c4f720c16457eea75
  size: 202834
  hash: md5
  path: sensors.csv
```

Comparez la valeur `md5` de ce fichier au paramètre `data_md5` de votre dernier run MLflow. Que constatez-vous ?

L'empreinte MD5 du fichier DVC doit être identique au paramètre `data_md5` du run MLflow entraîné sur cette même version du dataset. Pour v2, cette empreinte est `93fdeef2cac1893c4f720c16457eea75`.

Pourquoi `data/sensors.csv` ne va pas dans Git, alors que `data/sensors.csv.dvc` y va ?

Le fichier CSV contient les données elles-mêmes. DVC gère ces données volumineuses dans son cache et son stockage distant.

Le fichier `.dvc` est un petit fichier de métadonnées qui contient notamment l'empreinte MD5 et permet de retrouver la version correspondante des données. Il peut donc être versionné dans Git.

Après `python -m maintai.dataset --n 8000 --seed 7`, que dit `dvc status` ?

```text
data/sensors.csv.dvc:
    changed outs:
        modified: data/sensors.csv
```

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Nombre de lignes |
|---|---|---|---:|
| v1 | `7d3c307` | À récupérer depuis le reçu DVC v1 | 5000 |
| v2 | `da819ea` | `93fdeef2` | 8000 |

Revenez à la v1 (`git checkout <commit> -- data/sensors.csv.dvc`, puis `dvc checkout`). Combien de lignes contient `data/sensors.csv` ? Puis revenez à la v2.

La version v1 contient 5 000 lignes. Cela a été vérifié avec la commande :

```text
5000 relevés écrits dans data/sensors.csv
Rows: 5000
```

La version v2 contient 8 000 lignes. Le changement entre les deux versions permet de retrouver les données correspondant au reçu DVC sélectionné.

Supprimez `data/sensors.csv` et le dossier `.dvc/cache`, puis lancez `dvc pull`. Que se passe-t-il ?

DVC utilise le fichier `data/sensors.csv.dvc` pour identifier la version demandée grâce à son empreinte MD5. Il récupère ensuite les données correspondantes depuis le stockage distant configuré et restaure le fichier CSV.

La sortie réelle de cette manipulation reste à ajouter après son exécution.

## 4. Relier modèle et données

Entraînez un modèle sur la v2. Dans `mlflow ui`, comparez ce run à celui de la v1 avec les mêmes réglages :

| Run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---:|---:|---:|
| v1 | À récupérer dans MLflow | 4000 | 0.838 | 0.543 |
| v2 | `93fdeef2` | 6400 | 0.824 | 0.567 |

Run MLflow v2 : `01a9f2457f7b43ceaebaeb7f451d93be`.

Peut-on dire que le modèle v2 est « meilleur » ? Pourquoi faut-il être prudent en comparant deux runs entraînés sur des données différentes ?

On ne peut pas affirmer que le modèle v2 est meilleur dans tous les aspects. Son accuracy et sa precision sont meilleures, mais son recall est légèrement inférieur à celui de v1.

Il faut rester prudent car les deux modèles ont été entraînés et évalués sur des datasets différents. Les exemples utilisés pour l'entraînement et les tests ne sont donc pas nécessairement les mêmes. Une comparaison fiable nécessite un protocole d'évaluation identique.

## 5. Décision : l'ADR 004

Dans `docs/adr/004-choix-du-modele.md`, nous retenons la régression logistique avec un seuil de classification de 0.2.

Ce choix privilégie le recall afin de réduire le nombre de pannes non détectées, même si cela entraîne davantage de fausses alertes.

- Run MLflow de validation sur v2 : `01a9f2457f7b43ceaebaeb7f451d93be`
- `data_md5` de v2 : `93fdeef2cac1893c4f720c16457eea75`

## 6. Questions de compréhension

1. Quelle différence entre Git, DVC et MLflow ? Que versionne chacun ?

   Git versionne le code source et les fichiers de métadonnées comme les fichiers `.dvc`. DVC versionne les données volumineuses et permet de retrouver leurs différentes versions. MLflow suit les entraînements en enregistrant les paramètres, les métriques et les modèles.

2. Pourquoi le stockage DVC est-il ajouté avec `--local` dans ce TP ? Que faudrait-il pour que tout le groupe partage les mêmes données ?

   L'option `--local` enregistre la configuration du stockage dans `.dvc/config.local`, un fichier propre à la machine et non partagé dans Git. Pour partager les mêmes données, le groupe doit utiliser un stockage distant commun accessible à tous les membres et partager sa configuration dans Git.

3. Livrer un modèle, c'est trois choses (TP4). Lesquelles, et où sont-elles maintenant ?

   Il faut le code source, le modèle entraîné et les dépendances nécessaires pour le recharger. Le code est versionné dans Git, le modèle est conservé dans les artefacts MLflow et les dépendances sont indiquées dans le `requirements.txt` associé au modèle.

## 7. Le rendu Git

- Lien de la pull request : À compléter avec le lien de votre PR.
- Le tag `tp5` existe sur GitHub : À vérifier.
- `git status` avant le commit : À vérifier avec `git status --short --ignored`.

Les fichiers `mlflow.db`, `mlruns/`, `data/sensors.csv` et `.dvc/cache` ne doivent pas être ajoutés à Git.

## 8. Ce qui reste flou

La traçabilité entre Git, DVC et MLflow est comprise. Les versions des données peuvent être retrouvées avec DVC, tandis que MLflow permet de relier chaque entraînement à ses paramètres, ses métriques et à l'empreinte du dataset utilisé.