"""API Key management endpoints."""

from fastapi import APIRouter, Depends, Request, status

from app.core.audit import AuditAction, AuditOutcome, audit_log
from app.core.auth import get_current_user
from app.db import User
from app.dependencies import get_api_key_service
from app.schemas.api_key import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse
from app.services.api_key_service import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _get_ip_address(request: Request) -> str | None:
    """Extract client IP address from request."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: Request,
    payload: APIKeyCreate,
    service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> APIKeyCreatedResponse:
    """Create a new API key.

    The key is only returned once at creation. Store it securely!
    """
    api_key, plain_key = service.create_api_key(
        user=current_user,
        name=payload.name,
        expires_at=payload.expires_at,
        scopes=payload.scopes,
    )

    audit_log(
        AuditAction.CREDENTIAL_CREATE,
        AuditOutcome.SUCCESS,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="api_key",
        resource_id=str(api_key.id),
        resource_name=api_key.name,
        details={"key_prefix": api_key.key_prefix},
    )

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[APIKeyResponse])
def list_api_keys(
    service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> list[APIKeyResponse]:
    """List all API keys for the current user."""
    keys = service.list_user_api_keys(current_user)
    return [APIKeyResponse.model_validate(key) for key in keys]


@router.get("/{key_id}", response_model=APIKeyResponse)
def get_api_key(
    key_id: int,
    service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> APIKeyResponse:
    """Get an API key by ID."""
    api_key = service.get_api_key(key_id, current_user)
    return APIKeyResponse.model_validate(api_key)


@router.post("/{key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    request: Request,
    service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke an API key (deactivate without deleting)."""
    api_key = service.get_api_key(key_id, current_user)
    key_name = api_key.name

    service.revoke_api_key(key_id, current_user)

    audit_log(
        AuditAction.CREDENTIAL_UPDATE,
        AuditOutcome.SUCCESS,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="api_key",
        resource_id=str(key_id),
        resource_name=key_name,
        details={"action": "revoke"},
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
    request: Request,
    service: APIKeyService = Depends(get_api_key_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Permanently delete an API key."""
    api_key = service.get_api_key(key_id, current_user)
    key_name = api_key.name

    service.delete_api_key(key_id, current_user)

    audit_log(
        AuditAction.CREDENTIAL_DELETE,
        AuditOutcome.SUCCESS,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="api_key",
        resource_id=str(key_id),
        resource_name=key_name,
    )
