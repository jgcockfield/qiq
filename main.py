from fastapi import FastAPI, Body
from typing import Any, Dict
from pydantic import RootModel
from fastapi.middleware.cors import CORSMiddleware
from app.engine.evaluator import evaluate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

class EvaluatePayload(RootModel[Dict[str, Any]]):
    pass


@app.post("/evaluate")
async def run_evaluate(payload: EvaluatePayload = Body(default={})):
    return evaluate(payload.root)
