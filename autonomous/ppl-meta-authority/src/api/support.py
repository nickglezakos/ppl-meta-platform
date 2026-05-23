from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.admin import AuthorityUserRecord
from core.auth import require_support_or_platform_admin
from core.storage import get_authority_user_by_uuid, set_authority_user_status

router = APIRouter(prefix="/api/v1/support", tags=["support"])


class SupportReinstateUserRequest(BaseModel):
    reason_code: str = Field(min_length=1)
    operator_note: str | None = None


@router.patch("/users/{user_uuid}/reinstate", response_model=AuthorityUserRecord)
async def support_reinstate_user(
    user_uuid: str,
    payload: SupportReinstateUserRequest,
    current_user: dict[str, str] = Depends(require_support_or_platform_admin),
) -> AuthorityUserRecord:
    target_user = get_authority_user_by_uuid(user_uuid)
    if target_user is None:
        raise HTTPException(status_code=404, detail="Authority user not found")
    if target_user["role_name"] not in {"owner", "reseller"}:
        raise HTTPException(status_code=403, detail="Support may only reinstate owner or reseller users")
    if target_user["status"] != "suspended":
        raise HTTPException(status_code=400, detail="Support emergency reinstatement only applies to suspended users")

    try:
        user = set_authority_user_status(
            user_uuid=user_uuid,
            status="active",
            actor_user_uuid=current_user.get("user_uuid"),
            actor_role_name=current_user.get("role_name"),
            reason_code=payload.reason_code,
            operator_note=payload.operator_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AuthorityUserRecord(**user)
