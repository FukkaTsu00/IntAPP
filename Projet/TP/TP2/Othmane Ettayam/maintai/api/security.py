"""Authentification par clé API, transmise dans l'en-tête X-API-Key."""
import secrets

from fastapi import Header, HTTPException, status

from maintai.config import get_settings


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
