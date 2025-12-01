"""Role and tenant permissions for DRF."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS

if TYPE_CHECKING:
    from webnet.customers.models import Customer


def _customer_ids_for_user(user) -> list[int]:
    return list(user.customers.values_list("id", flat=True))


def user_has_customer_access(user, customer_id: int | None) -> bool:
    if not user or not user.is_authenticated or customer_id is None:
        return False
    if getattr(user, "role", "viewer") == "admin":
        return True
    return customer_id in _customer_ids_for_user(user)


def resolve_customer_for_request(request) -> "Customer | None":
    """Resolve customer from request data/params with access validation.

    Used by CommandViewSet and ConfigViewSet to determine target customer.
    Returns None if customer cannot be resolved or access is denied.
    """
    from webnet.customers.models import Customer

    customer_id = request.data.get("customer_id") or request.query_params.get("customer_id")
    user = request.user

    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return None
        if not user_has_customer_access(user, customer.id):
            return None
        return customer

    # Fallback: single assigned customer for non-admin users
    if getattr(user, "role", "viewer") != "admin" and user.customers.count() == 1:
        return user.customers.first()

    return None


def resolve_customer_id(obj):
    direct = getattr(obj, "customer_id", None) or getattr(
        getattr(obj, "customer", None), "id", None
    )
    if direct:
        return direct
    for rel in ("policy", "device", "job"):
        rel_obj = getattr(obj, rel, None)
        if rel_obj:
            cid = getattr(rel_obj, "customer_id", None) or getattr(
                getattr(rel_obj, "customer", None), "id", None
            )
            if cid:
                return cid
    return None


class RolePermission(BasePermission):
    """Enforce viewer/operator/admin semantics.

    - viewer: read-only
    - operator: read + POST (job creation, actions)
    - admin: full access
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "role", "viewer") == "admin":
            return True
        if user.role == "operator":
            return request.method in SAFE_METHODS or request.method == "POST"
        if user.role == "viewer":
            return request.method in SAFE_METHODS
        return False


class CustomerScopedQuerysetMixin:
    """Filter queryset to the user's customers unless admin.

    Set ``customer_field`` to a string or tuple of dotted lookups (e.g. ``"customer_id"``
    or ("policy__customer_id", "device__customer_id")) to scope correctly.
    """

    customer_field: str | tuple[str, ...] = "customer_id"

    def get_queryset(self):  # pragma: no cover - wrapper
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return qs.none()
        if getattr(user, "role", "viewer") == "admin":
            return qs
        customer_ids = _customer_ids_for_user(user)
        if not customer_ids:
            return qs.none()
        fields = self.customer_field
        if isinstance(fields, str):
            fields = (fields,)
        q = Q()
        for field in fields:
            q |= Q(**{f"{field}__in": customer_ids})
        return qs.filter(q)


class ObjectCustomerPermission(BasePermission):
    """Object-level check on customer ownership for non-admins."""

    def has_object_permission(self, request, view, obj):  # pragma: no cover - simple guard
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "role", "viewer") == "admin":
            return True
        customer_id = resolve_customer_id(obj)
        return user_has_customer_access(user, customer_id)
