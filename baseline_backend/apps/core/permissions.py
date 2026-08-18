"""
Centralized RBAC permission checking.

Project context Section 8, "Never happen": role/permission checks inlined ad
hoc in view logic instead of routed through this layer. Every authorization
decision in the codebase — DRF view, service function, admin action — calls
`has_permission()` (or the `RequirePermission` DRF permission class below),
never `if request.membership.role == "admin"` inline.

Full request-level authz order (Section 2): AuthN -> tenant/membership
re-validation (TenantContextMiddleware) -> RBAC (this module) -> object-level
ownership check (left to each viewset's get_queryset(), which is already
tenant-filtered by TenantScopedManager).
"""
from functools import lru_cache

from rest_framework.permissions import BasePermission

from apps.core.models import Membership, RolePermission


@lru_cache(maxsize=1)
def _role_permission_map() -> dict[str, frozenset[str]]:
    """role -> frozenset of codenames it grants. Cached process-wide: this
    table changes only via migration/seed script, never at runtime, so a
    per-request DB hit for it is pure waste. Cache is keyed on nothing
    (maxsize=1) — call `_role_permission_map.cache_clear()` after any
    migration that reseeds RolePermission, e.g. in a post-migrate signal or
    deploy hook, so a running process doesn't serve a stale map.
    """
    mapping: dict[str, set[str]] = {role: set() for role, _ in Membership.Role.choices}
    for rp in RolePermission.objects.select_related("permission").all():
        mapping.setdefault(rp.role, set()).add(rp.permission.codename)
    return {role: frozenset(codes) for role, codes in mapping.items()}


def has_permission(role: str, codename: str) -> bool:
    """codename format: 'resource:action', e.g. 'invoices:create'."""
    return codename in _role_permission_map().get(role, frozenset())


class RequirePermission(BasePermission):
    """DRF permission class factory.

    Usage:
        class InvoiceViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, RequirePermission("invoices:create")]

    For viewsets needing different permissions per action, override
    `get_permissions()` and instantiate this per-action instead of listing
    it statically in `permission_classes`.
    """

    def __init__(self, codename: str):
        self.codename = codename

    def __call__(self):
        # DRF instantiates permission_classes entries with no args; this
        # makes RequirePermission("x:y") itself callable so it can be used
        # directly in the permission_classes list.
        return self

    def has_permission(self, request, view) -> bool:
        membership = getattr(request, "membership", None)
        if membership is None:
            return False
        return has_permission(membership.role, self.codename)
