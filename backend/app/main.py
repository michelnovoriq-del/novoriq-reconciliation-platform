from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, files, health, match_results, reconciliation_runs


app = FastAPI(
    title="Novoriq Reconciliation Agent API",
    version="0.1.0",
    description="Phase 1 backend foundation for CSV/Excel reconciliation workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(reconciliation_runs.router)
app.include_router(match_results.router)
