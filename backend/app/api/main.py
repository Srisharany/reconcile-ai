from fastapi import FastAPI

from app.api.routes import router


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="ReconcileAI",
    description=(
        "Autonomous Multi-Source "
        "Financial Reconciliation System"
    ),
    version="0.1.0",
)


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
def root():

    return {
        "name": "ReconcileAI",
        "status": "running",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
    }


app.include_router(
    router
)