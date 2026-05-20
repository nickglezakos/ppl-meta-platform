from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from core.auth import bootstrap_admin_enabled, require_authority_user
from core.storage import (
    authenticate_authority_user,
    bootstrap_authority_admin,
    create_authority_user_from_invitation,
    create_authority_session,
    create_authority_user,
    get_authority_user_by_email,
    revoke_authority_session,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class AuthorityUserResponse(BaseModel):
    user_uuid: str
    email: str
    display_name: str | None = None
    role_name: str
    status: str
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    display_name: str | None = None
    role_name: str = Field(default="owner", pattern="^(owner|reseller|distributor|support)$")
    distributor_uuid: str | None = None
    reseller_uuid: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class AcceptInvitationRequest(BaseModel):
    invitation_token: str
    password: str = Field(min_length=8)
    display_name: str | None = None


class SessionResponse(BaseModel):
    session_token: str
    expires_at: str
    user: AuthorityUserResponse


@router.post("/register", response_model=AuthorityUserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> AuthorityUserResponse:
    existing = get_authority_user_by_email(payload.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Authority user already exists")

    user = create_authority_user(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        role_name=payload.role_name,
        distributor_uuid=payload.distributor_uuid,
        reseller_uuid=payload.reseller_uuid,
    )
    return AuthorityUserResponse(**user)


@router.post("/accept-invitation", response_model=AuthorityUserResponse, status_code=status.HTTP_201_CREATED)
async def accept_invitation(payload: AcceptInvitationRequest) -> AuthorityUserResponse:
    try:
        user = create_authority_user_from_invitation(
            invitation_token=payload.invitation_token,
            password=payload.password,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AuthorityUserResponse(**user)


@router.post("/login", response_model=SessionResponse)
async def login(payload: LoginRequest) -> SessionResponse:
    user = authenticate_authority_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session = create_authority_session(user_uuid=user["user_uuid"])
    return SessionResponse(
        session_token=session["session_token"],
        expires_at=session["expires_at"],
        user=AuthorityUserResponse(**user),
    )


@router.get("/me", response_model=AuthorityUserResponse)
async def me(current_user: dict[str, str] = Depends(require_authority_user)) -> AuthorityUserResponse:
    return AuthorityUserResponse(**current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: dict[str, str] = Depends(require_authority_user)) -> Response:
    revoke_authority_session(current_user["session_token"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bootstrap-admin", response_model=AuthorityUserResponse)
async def bootstrap_admin() -> AuthorityUserResponse:
    if not bootstrap_admin_enabled():
        raise HTTPException(status_code=403, detail="Bootstrap admin flow is disabled")

    user = bootstrap_authority_admin(
        email="admin@authority.local",
        password="change-this-admin-password",
        display_name="Authority Admin",
    )
    return AuthorityUserResponse(**user)
