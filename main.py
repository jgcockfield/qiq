from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.engine.evaluator import evaluate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/evaluate")
async def run_evaluate(request: Request):
    payload = await request.json()
    return evaluate(payload)
