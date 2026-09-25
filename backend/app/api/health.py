"""Health check route. Does not call the model."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
