# Étude de conception — Prédiction de pannes

Groupe : G2 · Version : finale · Date : 27/10/2026

## 1. Contexte et utilisateurs
- Utilisateur principal (un rôle précis) : Technicien / Responsable maintenance d'un parc d'équipements.
- Contexte : À partir de relevés de capteurs, il faut aider à anticiper un risque de panne pour prioriser les interventions.

## 2. Problème et décision
- Décision que l'utilisateur prend avec le système : Intervenir préventivement sur l'équipement (ou non) en fonction du risque de panne prédit.
- Fréquence : À chaque nouveau relevé / de manière journalière selon le suivi du parc.
- Coût d'une erreur, et pour qui : 
  - Faux négatif (panne non détectée) : coût élevé (immobilisation, réparation urgente, impact production/sécurité) pour l'exploitation.
  - Faux positif (intervention inutile) : coût moindre (temps technicien, pièces) mais à limiter.

## 3. Approche par sous-problème
| Sous-problème | Approche (règles / ML / DL / LLM / RAG) | Pourquoi pas une approche plus simple |
|---|---|---|
| Prédire la survenance / l'état lié à une panne | Apprentissage supervisé (classification) | Des règles métier à seuils fixes sont trop rigides : elles ne capturent pas les combinaisons de mesures entre capteurs et se dégradent selon les équipements. |
| Comparer objectivement les modèles | Comparaison systématique avec une baseline + plusieurs modèles | Nécessaire pour justifier le choix du modèle retenu (meilleur compromis performance / simplicité) plutôt qu'un choix arbitraire. |

## 4. Données
| Jeu de données | Source et licence | Volume | Données personnelles ? |
|---|---|---|---|
| `data/exemple_pannes.csv` | Fourni dans le cadre du TP (usage pédagogique) | À préciser après inspection (lignes/colonnes) | Non (données techniques / mesures de capteurs) |

## 5. Métriques, baseline et critères d'acceptation
- Métriques calculées (`monprojet/train.py`, fonction `evaluate()`) :
  - Classification : `accuracy`, `recall`, `precision`, `f1`
  - Régression : `mae`, `rmse`, `r2`
- Baseline et son score : `baseline` = `DummyClassifier(strategy="most_frequent")` (classification) ou `DummyRegressor(strategy="mean")` (régression), placée en tête de `candidates()`. Son score est mesuré sur le jeu de test comme pour les autres modèles.
- Métrique principale, et pourquoi : `recall` (`MAIN_METRIC = "recall"` dans `config.py`). En classification binaire, il mesure la part des pannes réelles effectivement détectées : c'est la métrique qui pénalise les faux négatifs, dont le coût est le plus élevé (section 2).
- Modèles comparés : `baseline`, `logistic_regression`, `decision_tree`, `random_forest`.
- Critères d'acceptation (métrique, nombre, jeu de données, condition) : Le modèle retenu doit obtenir un `recall` supérieur à celui de la baseline sur le jeu de test (`data/exemple_pannes.csv`, split défini dans `config.py`). Les résultats doivent être reportés dans `docs/choix-modele.md`.

### Résultats obtenus (jeu de test)

| Modèle | accuracy | recall | precision | f1 |
|---|---|---|---|---|
| baseline (`DummyClassifier`) | 0.824 | 0.0 | 0.0 | 0.0 |
| logistic_regression | 0.889 | 0.574 | 0.737 | 0.645 |
| **decision_tree** (retenu) | 0.839 | **0.597** | 0.538 | 0.566 |
| random_forest | 0.873 | 0.545 | 0.671 | 0.602 |

- Meilleur modèle selon `MAIN_METRIC = "recall"` : `decision_tree` (recall = 0.597).
- Écart avec la baseline : +0.597 de recall (0.597 contre 0.0).
- Critère d'acceptation : atteint (recall du modèle retenu > recall de la baseline).
- Remarque : `random_forest` a une meilleure accuracy (0.873) et un meilleur f1 que `decision_tree`, mais un recall inférieur ; le choix reste cohérent avec la métrique principale (détecter un maximum de pannes réelles).

## 6. Architecture prévue
- Chargement des données : `monprojet/data.py` (`load_data()`)
- Découpage train/test : `monprojet/data.py` (`split()`) selon `SPLIT` / `TIME_COLUMN` si série temporelle
- Prétraitement : `feature_columns()` et `build_preprocessing()` fournis
- Candidats de modèles : `monprojet/models.py` (`candidates()`) — baseline en premier, puis au moins 3 modèles
- Entraînement/évaluation : `monprojet/train.py` (`evaluate()`, `main()`) 
- Sorties : `models/model.joblib` (meilleur modèle selon `MAIN_METRIC`), `models/metrics.json` (scores de tous les modèles)

## 7. Choix technologiques
- Langage : Python
- Données : pandas
- ML : scikit-learn
- Sauvegarde : joblib
- Tests : pytest

## 8. Risques, éthique, confidentialité
- Données : uniquement des mesures techniques, pas de données personnelles identifiables dans le jeu fourni.
- Biais / généralisation : risque de surapprentissage si peu de données. Le découpage train/test et la comparaison avec une baseline visent à limiter ce risque.
- Sécurité / usage : ce modèle est un outil d'aide à la décision, non un substitut à un diagnostic métier.

## 9. Limites et hors périmètre
- Hors périmètre : déploiement en production, monitoring, explicabilité poussée, optimisation temps-réel.
- Limites : performances limitées par la taille/qualité du jeu de données fourni, hypothèse de représentativité et simplicité imposée par le cadre du TP.
