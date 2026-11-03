import pytest
HEADERS = {"X-API-Key": "test-key"} # la clé des tests (conftest.py) ; inutile en TP1, nécessaire en TP2
VALID = {"temperature_c": 60.0, "vibration_mm_s": 2.0, "load_pct": 50.0, "runtime_hours": 5000}

CAS_REFUSES = [
    # 1. Charge supérieure à 100 %
    ("valeur absurde", "/v1/predict",
     {**VALID, "load_pct": 250}, 422),

    # 2. Température négative
    ("temperature negative", "/v1/predict",
     {**VALID, "temperature_c": -100}, 422),

    # 3. Vibration négative
    ("vibration negative", "/v1/predict",
     {**VALID, "vibration_mm_s": -5}, 422),

    # 4. Charge sous zéro
    ("charge negative", "/v1/predict",
     {**VALID, "load_pct": -10}, 422),

    # 5. Durée de fonctionnement négative
    ("runtime negative", "/v1/predict",
     {**VALID, "runtime_hours": -100}, 422),
]

@pytest.mark.parametrize("description, url, corps, attendu", CAS_REFUSES)
def test_requete_refusee(client, description, url, corps, attendu):
    assert client.post(url, json=corps, headers=HEADERS).status_code == attendu