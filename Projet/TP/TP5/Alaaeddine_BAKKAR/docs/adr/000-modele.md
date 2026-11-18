# ADR 000 : Choix du modèle et du seuil de classification

Date : 18/11/2026 · Auteurs : Alaaeddine Bakkar

## Contexte

Le module de prédiction de MaintAI doit anticiper les pannes des capteurs industriels avant qu'elles ne surviennent. Dans un contexte de maintenance prédictive, une panne manquée (faux négatif) peut entraîner un arrêt de production coûteux, alors qu'une fausse alerte (faux positif) nécessite principalement une vérification préventive. Il faut donc sélectionner un modèle et un seuil de décision qui privilégient le rappel (`recall`).

## Options étudiées

1. **Régression logistique par défaut (`C=1.0`, `threshold=0.3`)** : offre un bon équilibre global (`accuracy = 0.904`, `precision = 0.622`), mais ne détecte que 75 % des pannes (`recall = 0.750`).
2. **Régression logistique fortement régularisée (`C=0.01`, `threshold=0.3`)** : obtient la meilleure précision (`0.653`) et la meilleure exactitude (`0.908`), mais détecte moins de pannes (`recall = 0.691`).
3. **Forêt aléatoire (`--model forest`)** : donne des résultats inférieurs à la régression logistique dans nos expériences (`recall = 0.728` au seuil de `0.3`).
4. **Régression logistique avec seuil abaissé (`C=1.0`, `threshold=0.2`)** : permet de détecter 83,8 % des pannes (`recall = 0.838`), au prix d'une augmentation des fausses alertes (`precision = 0.543`, `accuracy = 0.882`).

## Décision

Retenir le modèle de **régression logistique (`C=1.0`) avec un seuil de décision à `0.2`** (`python -m maintai.train --threshold 0.2`).

- **Run MLflow :** Run ID `18322a7e007141bfbea3f962092610b6` (expérience avec le seuil de `0.2` sur le dataset v1).
- **Version des données :** dataset v1 contenant 5 000 lignes. L'empreinte MD5 exacte doit être récupérée depuis le fichier `data/sensors.csv.dvc` du commit v1.

## Conséquences

- **Ce que cette décision facilite :** Réduction du nombre de pannes non détectées, temps d'inférence minimal et traçabilité des expériences grâce à MLflow et au versionnement des données avec DVC.
- **Ce que cela rend plus difficile :** Augmentation du taux de fausses alertes (`precision = 0.543`), ce qui peut générer davantage de contrôles préventifs pour les équipes de maintenance.
- **Ce qu'il faudra surveiller :** L'acceptabilité du volume de fausses alertes par les opérateurs, ainsi que l'évolution des performances sur la version v2 du dataset (8 000 lignes). Avec cette version, le Recall mesuré est de `0.824`, contre `0.838` sur v1.