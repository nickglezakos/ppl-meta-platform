from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.installations import EntitlementRecord, InstallationUpsertRequest
from core.auth import require_admin_token
from core.storage import delete_entitlement, get_entitlement_by_uuid, list_entitlements, upsert_entitlement

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])


@router.get("/installations", response_model=list[EntitlementRecord])
async def admin_list_installations() -> list[EntitlementRecord]:
    return [EntitlementRecord(**record) for record in list_entitlements()]


@router.post("/installations", response_model=EntitlementRecord)
async def admin_upsert_installation(payload: InstallationUpsertRequest) -> EntitlementRecord:
    record = upsert_entitlement(payload.model_dump(exclude_none=True))
    return EntitlementRecord(**record)


@router.get("/installations/{entitlement_uuid}", response_model=EntitlementRecord)
async def admin_get_installation(entitlement_uuid: str) -> EntitlementRecord:
    record = get_entitlement_by_uuid(entitlement_uuid)
    if record is None:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    return EntitlementRecord(**record)


@router.delete("/installations/{entitlement_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_installation(entitlement_uuid: str) -> Response:
    deleted = delete_entitlement(entitlement_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entitlement not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)