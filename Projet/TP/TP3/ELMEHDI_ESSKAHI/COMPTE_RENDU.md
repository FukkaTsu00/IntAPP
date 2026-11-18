# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** G2  ·  **Membres :** EL MEHDI ES-SAKHI  ·  **Date :** …

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP3.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
5 failed, 18 passed, 1 warning in 13.82s
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

FAILED tests/test_client.py::test_client_returns_prediction - NotImplementedError: TP3 sprint 2 : MaintaiClient.predict
FAILED tests/test_client.py::test_client_wrong_key_raises_401 - NotImplementedError: TP3 sprint 2 : MaintaiClient.predict
FAILED tests/test_client.py::test_client_bad_reading_raises_422 - NotImplementedError: TP3 sprint 2 : MaintaiClient.predict
FAILED tests/test_ui.py::test_ui_shows_the_data - IndexError: list index out of range
FAILED tests/test_ui.py::test_ui_shows_the_prediction - IndexError: list index out of range

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

Python cherche les modules dans une liste de dossiers (`sys.path`). Avec `streamlit run ui/app.py`, seul le dossier du script (`ui/`) y est ajouté : `maintai/` n'y est pas, d'où l'erreur. Avec `python -m streamlit run ui/app.py`, Python ajoute le dossier courant (TP3), qui contient `maintai/`, donc l'import réussit. Cela ne marche que depuis TP3 : c'est ce que le package du TP4 corrige.


## 3. Sprint 1 : l'onglet « Données »

Votre code de l'onglet « Données » (de `c1, c2, c3 = ...` jusqu'au nuage de points) :

```python
with onglet_donnees:
    df = charger(get_settings().data_path)

    # 1. Trois indicateurs côte à côte
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Nombre de relevés", len(df))

    with col2:
        st.metric("Taux de panne", f"{df['failure'].mean() * 100:.2f} %")

    with col3:
        st.metric("Température moyenne", f"{df['temperature_c'].mean():.2f} °C")

    st.divider()

    # 2. Liste déroulante pour choisir une variable
    variable = st.selectbox(
        "Choisir une variable :",
        FEATURES
    )

    # 3. Taux de panne par tranche de la variable choisie
    st.subheader(f"Taux de panne selon {variable}")

    df_temp = df[[variable, "failure"]].copy()

    # Découpage de la variable en 5 intervalles
    df_temp["tranche"] = pd.cut(df_temp[variable], bins=5)

    # Calcul du taux de panne pour chaque tranche
    taux_panne = (
        df_temp.groupby("tranche", observed=False)["failure"]
        .mean()
        .mul(100)
        .reset_index()
    )

    # Conversion des intervalles en chaînes de caractères
    taux_panne["tranche"] = taux_panne["tranche"].astype(str)

    # Affichage du graphique
    st.bar_chart(
        taux_panne,
        x="tranche",
        y="failure"
    )

    st.divider()

    # 4. Nuage de points température / vibration
    st.subheader("Température / Vibration selon les pannes")

    st.scatter_chart(
        df,
        x="temperature_c",
        y="vibration_mm_s",
        color="failure"
    )
```

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000|
| Taux de panne | 13.6%|
| Température moyenne |59.80 °C |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

Le taux de panne augmente avec la vibration : il passe d'environ ⟦X⟧ % pour la tranche la plus basse à environ ⟦Y⟧ % pour la plus haute (valeurs lues sur le graphique ou données par `verifier_valeurs.py`). Les tranches extrêmes contiennent peu de relevés, donc leur taux est moins fiable.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal, et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

Si le curseur est dans un `st.form` : rien ne s'affiche tant qu'on ne clique pas sur « Prédire », puis « relance » apparaît une fois. Si le curseur est hors du formulaire : « relance » s'affiche à chaque déplacement. Dans les deux cas, cela montre que Streamlit exécute à nouveau tout le script, de la première à la dernière ligne, à chaque interaction, et que `st.form` sert à regrouper les widgets pour ne provoquer qu'une seule relance.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Comme tout le script est relancé à chaque interaction, sans cache le CSV de 5000 lignes serait relu à chaque clic. Avec `@st.cache_data`, il est lu une seule fois ; les relances suivantes réutilisent le tableau gardé en mémoire.


## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python

def predict(self, reading: dict) -> dict:
    """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""

    # 1. Préparer les en-têtes
    headers = {}
    if self.api_key:
        headers["X-API-Key"] = self.api_key

    # 2. Envoyer la requête POST
    r = self.http.post(
        "/v1/predict",
        json=reading,
        headers=headers
    )

    # 3. Vérifier le code HTTP
    if r.status_code != 200:
        detail = r.json().get("detail")
        raise APIError(r.status_code, detail)

    # 4. Retourner la réponse JSON
    return r.json()

```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
1 failed, 22 passed, 1 warning in 10.07s
```

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai                                           | Ce qu'affiche Streamlit                                          |
| ----------------------------------------------- | ---------------------------------------------------------------- |
| valeurs par défaut, bonne clé                   | « Probabilité de panne : 95 % » puis un message rouge « ALERTE » |
| valeurs par défaut, fausse clé                  | Avertissement jaune « Erreur 401 : Clé API absente ou invalide » |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | Message rouge « API injoignable : uvicorn est-il lancé ? »       |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?


CORS est une règle appliquée par le navigateur

## 5. Questions de compréhension

1. **Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?**
   TP2 : le navigateur de l'utilisateur (JavaScript `fetch`). TP3 : le serveur Streamlit (Python, `MaintaiClient` avec `httpx`). Le navigateur ne parle qu'à Streamlit.
2. **Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?**
   Le test passe à `MaintaiClient` un client de test (`http=client`) branché directement sur l'application FastAPI : la requête est traitée en mémoire, sans réseau ni serveur. Cela n'est possible que parce que `predict` utilise `self.http.post` et non `httpx.post`.
3. **Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien ?**
   Démo client : HTML + JavaScript, car on contrôle l'apparence et l'image de marque ; on accepte un développement plus long. Technicien : Streamlit, car l'équipe maîtrise Python, l'outil est prêt en une séance et une interface fonctionnelle suffit ; on renonce à une personnalisation poussée.

## 6. Le rendu Git

- Lien de la pull request : …
- Le tag `tp3` existe sur GitHub : oui / non
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? oui / non

## 7. Ce qui reste flou

…
