# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** ⟦numéro de groupe⟧ · **Membres :** Alaaeddine BAKKAR, ⟦autres membres⟧ · **Date :** 10/11/2026

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
5 failed, 18 passed
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

Deux fichiers échouent. `tests/test_client.py` : un test échoue avec `NotImplementedError`, car le corps de `MaintaiClient.predict` est encore un TODO. `tests/test_ui.py` : quatre tests échouent (`IndexError: list index out of range`), car les onglets « Données » et « Prédiction » ne contiennent que des TODO. Les éléments que les tests cherchent (indicateurs, résultat de la prédiction) n'existent pas encore dans la page.

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
Traceback:
File ".../ui/app.py", line 10, in <module>
    from maintai.client import APIError, MaintaiClient
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

Python cherche les modules dans une liste de dossiers (`sys.path`). Avec `streamlit run ui/app.py`, seul le dossier du script (`ui/`) y est ajouté : `maintai/` n'y est pas, d'où l'erreur. Avec `python -m streamlit run ui/app.py`, Python ajoute le dossier courant (TP3), qui contient `maintai/`, donc l'import réussit. Cela ne marche que depuis TP3 : c'est ce que le package du TP4 corrige.

## 3. Sprint 1 : l'onglet « Données »

```python
df = charger(get_settings().data_path)

col1, col2, col3 = st.columns(3)
col1.metric("Relevés", len(df))
col2.metric("Taux de panne", f"{df['failure'].mean():.1%}")
col3.metric("Température moyenne", f"{df['temperature_c'].mean():.1f} °C")

variable = st.selectbox("Variable", FEATURES)

tranches = pd.cut(df[variable], bins=10)
taux_panne = df.groupby(tranches, observed=True)["failure"].mean()
taux_panne.index = [round(i.mid) for i in taux_panne.index]

st.subheader(f"Taux de panne selon {variable}")
st.bar_chart(taux_panne)

df_scatter = df.copy()
df_scatter["etat"] = df_scatter["failure"].map({0: "Non", 1: "Oui"})

st.subheader("Température et vibration selon les pannes")
st.scatter_chart(df_scatter, x="temperature_c", y="vibration_mm_s", color="etat")
```

| Indicateur          | Valeur affichée |
| ------------------- | --------------- |
| Relevés             | 5000            |
| Taux de panne       | 13,6 %          |
| Température moyenne | 59,8 °C         |

Choisissez `vibration_mm_s`. Comment évolue le taux de panne quand la vibration augmente ?

Le taux de panne augmente avec la vibration : il passe d'environ ⟦X⟧ % pour la tranche la plus basse à environ ⟦Y⟧ % pour la plus haute (valeurs lues sur le graphique ou données par `verifier_valeurs.py`). Les tranches extrêmes contiennent peu de relevés, donc leur taux est moins fiable.

Laquelle des deux variables compte le plus ?

On compare l'écart entre la barre la plus haute et la plus basse : environ ⟦écart température⟧ points pour la température et ⟦écart vibration⟧ points pour la vibration. La variable dont l'écart est le plus grand a l'effet le plus fort prise seule. Ce n'est pas une preuve de causalité, et les deux variables peuvent être corrélées entre elles.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal ?

⟦À tester vous-même.⟧ Si le curseur est dans un `st.form` : rien ne s'affiche tant qu'on ne clique pas sur « Prédire », puis « relance » apparaît une fois. Si le curseur est hors du formulaire : « relance » s'affiche à chaque déplacement. Dans les deux cas, cela montre que Streamlit exécute à nouveau tout le script, de la première à la dernière ligne, à chaque interaction, et que `st.form` sert à regrouper les widgets pour ne provoquer qu'une seule relance.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Comme tout le script est relancé à chaque interaction, sans cache le CSV de 5000 lignes serait relu à chaque clic. Avec `@st.cache_data`, il est lu une seule fois ; les relances suivantes réutilisent le tableau gardé en mémoire.

## 4. Sprint 2 : l'onglet « Prédiction »

```python
def predict(self, reading: dict) -> dict:
    """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
    headers = {"X-API-Key": self.api_key} if self.api_key else {}
    r = self.http.post("/v1/predict", json=reading, headers=headers)
    if r.status_code != 200:
        raise APIError(r.status_code, r.json().get("detail"))
    return r.json()
```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
23 passed
```

| Essai                                           | Ce qu'affiche Streamlit                                          |
| ----------------------------------------------- | ---------------------------------------------------------------- |
| valeurs par défaut, bonne clé                   | « Probabilité de panne : 95 % » puis un message rouge « ALERTE » |
| valeurs par défaut, fausse clé                  | Avertissement jaune « Erreur 401 : Clé API absente ou invalide » |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | Message rouge « API injoignable : uvicorn est-il lancé ? »       |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

CORS est une règle appliquée par le navigateur. En TP2, `fetch` s'exécutait dans le navigateur (page sur le port 5500), qui devait demander la permission à l'API (en-tête `Origin`), et la liste CORS décidait. En TP3, la requête part du serveur Streamlit (Python, via `httpx`), pas du navigateur : aucune vérification CORS n'a lieu, comme avec `curl` ou le client Java. La clé API reste vérifiée par l'API (401 si elle est fausse).

## 5. Questions de compréhension

1. **Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?**
   TP2 : le navigateur de l'utilisateur (JavaScript `fetch`). TP3 : le serveur Streamlit (Python, `MaintaiClient` avec `httpx`). Le navigateur ne parle qu'à Streamlit.
2. **Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?**
   Le test passe à `MaintaiClient` un client de test (`http=client`) branché directement sur l'application FastAPI : la requête est traitée en mémoire, sans réseau ni serveur. Cela n'est possible que parce que `predict` utilise `self.http.post` et non `httpx.post`.
3. **Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien ?**
   Démo client : HTML + JavaScript, car on contrôle l'apparence et l'image de marque ; on accepte un développement plus long. Technicien : Streamlit, car l'équipe maîtrise Python, l'outil est prêt en une séance et une interface fonctionnelle suffit ; on renonce à une personnalisation poussée.

## 6. Le rendu Git

- Lien de la pull request : ⟦coller l'URL de la PR⟧
- Le tag `tp3` existe sur GitHub : ⟦oui / non, après `git push --tags`⟧
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? ⟦non attendu ; à confirmer⟧

## 7. Ce qui reste flou

J'ai eu une `ImportError` de type « partially initialized module » parce que la ligne `from maintai.client import ...` s'était retrouvée dans `client.py` : un module ne doit pas s'importer lui-même. J'ai aussi perdu du temps sur la ligne de commande : `--env-file` et `pip install -e` exigent un argument (`.env` et `.`), et Streamlit échoue si on le lance depuis le mauvais dossier. Enfin, j'ai extrait le starter dans un sous-dossier (`TP3\maintai-starter-tp3`) au lieu du contenu directement dans `TP\TP3`, et je ne suis pas sûr de l'impact sur les chemins du dépôt Git. Je dois aussi mieux distinguer `sys.path` avec et sans `-m`.
