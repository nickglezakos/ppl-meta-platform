from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "ppl-meta-authority",
        "mode": "mvp",
    }


@router.get("/")
async def root() -> dict[str, object]:
    return {
        "service": "PPL Meta Authority",
        "description": "Minimal authority service for installation ownership and licence lifecycle.",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "installation_lookup": "/api/v1/installations/{installation_uuid}",
            "owner_status": "/api/v1/owners/{email}",
            "admin_installations": "/api/v1/admin/installations",
            "docs": "/docs",
        },
    }