from fastapi import FastAPI

app = FastAPI(
    title="ReconcileAI",
    description="Autonomous Multi-Source Reconciliation Agent",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "name": "ReconcileAI",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }