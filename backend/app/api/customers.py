"""Customer management API endpoints."""

from fastapi import APIRouter, Depends, status

from app.core.auth import get_current_user
from app.db import User
from app.dependencies import get_admin_user, get_customer_service
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.schemas.customer_ip_range import CustomerIPRangeCreate, CustomerIPRangeResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
    _: object = Depends(get_admin_user),
) -> CustomerResponse:
    """Create a new customer (admin only)."""
    customer = service.create_customer(payload)
    return CustomerResponse.model_validate(customer)


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user),
) -> list[CustomerResponse]:
    """List customers. Admins see all, others see assigned."""
    customers = service.list_customers(current_user)
    return [CustomerResponse.model_validate(customer) for customer in customers]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user),
) -> CustomerResponse:
    """Get customer details."""
    customer = service.get_customer(customer_id, current_user)
    return CustomerResponse.model_validate(customer)


@router.post("/{customer_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_user_to_customer(
    customer_id: int,
    user_id: int,
    service: CustomerService = Depends(get_customer_service),
    _: object = Depends(get_admin_user),
) -> None:
    """Assign a user to a customer (admin only)."""
    service.add_user_to_customer(customer_id, user_id)


@router.delete("/{customer_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_customer(
    customer_id: int,
    user_id: int,
    service: CustomerService = Depends(get_customer_service),
    _: object = Depends(get_admin_user),
) -> None:
    """Remove a user from a customer (admin only)."""
    service.remove_user_from_customer(customer_id, user_id)


@router.get("/{customer_id}/ranges", response_model=list[CustomerIPRangeResponse])
def list_customer_ip_ranges(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user),
) -> list[CustomerIPRangeResponse]:
    """List IP ranges for a customer."""
    ranges = service.list_ip_ranges(customer_id, current_user)
    return [CustomerIPRangeResponse.model_validate(r) for r in ranges]


@router.post(
    "/{customer_id}/ranges",
    response_model=CustomerIPRangeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_ip_range(
    customer_id: int,
    payload: CustomerIPRangeCreate,
    service: CustomerService = Depends(get_customer_service),
    _: object = Depends(get_admin_user),
) -> CustomerIPRangeResponse:
    """Add an IP range to a customer (admin only)."""
    ip_range = service.create_ip_range(customer_id, payload)
    return CustomerIPRangeResponse.model_validate(ip_range)


@router.delete("/{customer_id}/ranges/{range_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_ip_range(
    customer_id: int,
    range_id: int,
    service: CustomerService = Depends(get_customer_service),
    _: object = Depends(get_admin_user),
) -> None:
    """Delete an IP range (admin only)."""
    service.delete_ip_range(customer_id, range_id)
