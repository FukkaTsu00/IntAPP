"""API MaintAI : expose le modèle de prédiction de panne.

Lancement : uv run uvicorn maintai.api.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from maintai import __version__
from maintai.api.schemas import HealthOut, PredictionOut, SensorReading
from maintai.api.security import require_api_key
from maintai.config import get_settings
from maintai.predict import Predictor

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Charger le modèle une seule fois au démarrage
    try:
        state["predictor"] = Predictor.load(get_settings())
    except FileNotFoundError:
        # L'API démarre même si le modèle est absent
        state["predictor"] = None

    yield

    # Nettoyer l'état à l'arrêt
    state.clear()


app = FastAPI(
    title="MaintAI API",
    version=__version__,
    description="Prédiction de panne à partir de relevés de capteurs.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# Protéger toutes les routes /v1 avec une clé API
router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(require_api_key)],
)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        model_loaded=state.get("predictor") is not None,
    )


@router.post("/predict", response_model=PredictionOut)
def predict(reading: SensorReading) -> PredictionOut:
    predictor = state.get("predictor")

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modèle non chargé : lancez "
                "python -m maintai.train puis redémarrez l'API"
            ),
        )

    return PredictionOut(**predictor.predict(reading.model_dump()))


app.include_router(router)
