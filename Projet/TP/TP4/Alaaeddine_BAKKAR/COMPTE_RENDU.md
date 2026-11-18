# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** … · **Membres :** Alaaeddine BAKKAR · **Date :** 18/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP4.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```text
2 failed, 25 passed, 1 warning in 16.52s
```

Quels sont les deux tests qui échouent, et pourquoi ?

Le premier test est `test_installed_version_matches_the_code`, car le package `maintai` n'est pas encore installé dans l'environnement virtuel. Le deuxième test est `test_command_is_declared`, car la commande `maintai-predict` n'est pas encore déclarée dans la configuration du projet dans le fichier `pyproject.toml`.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

Vos sections `dependencies` et `[project.scripts]` :

```toml
dependencies = [
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "joblib>=1.4",
    "httpx>=0.27"
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

Pourquoi `pytest` et `fastapi` ne sont-ils pas dans `dependencies` ?

Parce qu'ils ne sont pas nécessaires pour effectuer une prédiction. `pytest` sert uniquement aux tests et `fastapi` est utilisé pour la partie API. Ils sont donc déclarés dans les dépendances optionnelles du projet.

Sortie de `pip show maintai` (les quatre premières lignes) :

```text
Name: maintai
Version: 0.2.0
Summary: TODO : une phrase qui dit ce que fait le package
Location: C:\Users\hp\Desktop\WORKDIR\IntAPP\Projet\TP\TP4\Alaaeddine_BAKKAR\.venv\Lib\site-packages
```

Dernière ligne de `python -m pytest` à la fin du Sprint 1 :

```text
27 passed, 1 warning in 9.80s
```

Placez-vous dans un autre dossier (`cd %TEMP%`) et lancez `maintai-predict 72 6 85 15000`, puis `python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python trouve-t-il le code de `maintai` ?

La commande `maintai-predict` fonctionne dans l'environnement TP4 et affiche :

```text
Probabilité de panne : 95 % (ALERTE)
```

Le test de localisation avec `python -c "import maintai; print(maintai.__file__)"` reste à effectuer dans un autre dossier.

Avec une installation en mode éditable (`pip install -e .`), Python utilise les fichiers sources du projet pour charger le package.

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller. Le changement est-il visible ? Pourquoi ?

Ce test reste à effectuer. Normalement, le changement est visible sans réinstallation, car l'option `-e` installe le package en mode éditable et utilise directement les fichiers sources.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```text
maintai-0.2.0.tar.gz
maintai-0.2.0-py3-none-any.whl
```

Contenu du wheel (`tar -tf dist\maintai-0.2.0-py3-none-any.whl`). Le modèle, les tests et `ui/` y sont-ils ? Pourquoi ?

```text
maintai/__init__.py
maintai/cli.py
maintai/client.py
maintai/config.py
maintai/data.py
maintai/dataset.py
maintai/predict.py
maintai/train.py
maintai/api/__init__.py
maintai/api/main.py
maintai/api/schemas.py
maintai/api/security.py
maintai-0.2.0.dist-info/METADATA
maintai-0.2.0.dist-info/WHEEL
maintai-0.2.0.dist-info/entry_points.txt
maintai-0.2.0.dist-info/top_level.txt
maintai-0.2.0.dist-info/RECORD
```

On y trouve uniquement le package Python `maintai` et ses fichiers de métadonnées. Le modèle, les tests et le dossier `ui/` ne sont pas inclus, car la configuration setuptools inclut uniquement les packages correspondant à `maintai*`. Le modèle doit donc être livré séparément du wheel.

Dans un environnement neuf (`%TEMP%\essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| Sans `MAINTAI_MODELS_DIR` | `Modèle introuvable` : le programme cherche `models/model.joblib` dans le dossier d'installation du package. |
| Avec `MAINTAI_MODELS_DIR` vers vos `models` | Erreur `ImportError: DLL load failed while importing _pocketfft_umath: An Application Control policy has blocked this file.` |
| Après `pip install scikit-learn==1.8.0` | Non vérifié à cause du blocage Windows lors du chargement des DLL NumPy/SciPy. |

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?

Cet avertissement apparaît lorsque le modèle a été entraîné avec une version de scikit-learn différente de celle utilisée pour le charger. Il faut comparer la version enregistrée lors de l'entraînement avec celle installée dans l'environnement de test.

La ligne exacte de `models/model_info.json` reste à vérifier.

**Problème rencontré :** Windows Application Control bloque le chargement d'une bibliothèque native utilisée par NumPy/SciPy dans l'environnement de test. L'installation du wheel a réussi, mais la prédiction dans cet environnement n'a pas pu être validée complètement.

## 4. Questions de compréhension

**1. Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?**

`requirements.txt` contient les versions des bibliothèques nécessaires pour reproduire un environnement précis. La liste `dependencies` de `pyproject.toml` contient les dépendances minimales nécessaires au fonctionnement du package, avec des contraintes de version comme `>=`.

**2. Quelle différence entre `pip install -e .` et `pip install dist\maintai-0.2.0-py3-none-any.whl` ?**

La première commande installe le package en mode éditable. Les modifications apportées au code source sont directement prises en compte. La deuxième installe une distribution construite au format wheel, indépendante du dossier source.

**3. Qu'est-ce qu'un « point d'entrée » (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict.exe` ?**

Un point d'entrée associe une commande utilisable dans le terminal à une fonction Python précise. Ici, `maintai-predict` appelle la fonction `main()` du fichier `maintai.cli`. Sous Windows, pip crée le fichier `maintai-predict.exe` dans le dossier `Scripts` de l'environnement virtuel.

## 5. Le rendu Git

- Lien de la pull request : …
- Le tag `tp4` existe sur GitHub : à vérifier.
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? À vérifier.

## 6. Ce qui reste flou

Le fonctionnement de la livraison du modèle séparément du wheel et la gestion des versions exactes de scikit-learn restent à approfondir. J'ai également rencontré un blocage Windows Application Control qui empêche le chargement de certaines bibliothèques natives dans l'environnement virtuel de test.