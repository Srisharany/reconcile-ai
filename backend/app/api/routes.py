"""
ReconcileAI API Router

Compatibility router.

The main dashboard API is implemented in app.main.
This router intentionally avoids defining duplicate API endpoints
with inconsistent response schemas.
"""

from fastapi import APIRouter


router = APIRouter(
    prefix="/api",
    tags=["ReconcileAI"],
)


@router.get("/router-status")
def router_status():
    return {
        "status": "active",
        "message": (
            "ReconcileAI dashboard endpoints are served "
            "by the main application API."
        ),
    }