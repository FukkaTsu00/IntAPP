from fastapi import FastAPI
from pydantic import BaseModel,Field
app = FastAPI()
class Reading(BaseModel):
    temperature: float = Field(ge=-40,le=150)
@app.get("/health")
def health():
    return {"status": "ok"}
@app.post("/v1/predict")
def predict(reading: Reading):
    return {"alert": reading.temperature > 80}