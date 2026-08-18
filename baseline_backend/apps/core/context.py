"""
Request-scoped tenant context.

This module is the single source of truth for "which tenant is this request
acting as." Both enforcement layers read from it:

  1. TenantScopedManager (apps/core/managers.py) — filters every queryset by
     the current tenant on the Python/ORM side.
  2. TenantContextMiddleware (apps/core/middleware.py) — writes the same
     value into Postgres via `SET LOCAL app.tenant_id`, which every RLS
     policy checks against.

The value is set exactly once per request, in TenantContextMiddleware, from
the authenticated user's re-validated Membership — never from a client-
supplied header, query param, or unvalidated token claim. Nothing outside
that middleware should call `set_current_tenant_id`; management commands and
background tasks use `tenant_context()` explicitly instead.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

_current_tenant_id: ContextVar[Optional[UUID]] = ContextVar(
    "current_tenant_id", default=None
)


class TenantContextError(Exception):
    """Raised when tenant-scoped code runs with no tenant context set.

    This is intentionally a hard failure, not a silent fall-through to an
    unscoped queryset — an unscoped queryset in a multi-tenant system is a
    data leak, not a convenience.
    """


def get_current_tenant_id() -> UUID:
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise TenantContextError(
            "No tenant context is set. Tenant-scoped models must only be "
            "queried inside a request handled by TenantContextMiddleware, "
            "or inside an explicit `with tenant_context(org_id):` block "
            "(management commands, Celery tasks, shell sessions)."
        )
    return tenant_id


def get_current_tenant_id_or_none() -> Optional[UUID]:
    """Non-raising variant for call sites that legitimately tolerate no context
    (e.g. platform_admin cross-tenant views, which use their own explicit
    superuser-gated queryset path rather than TenantScopedManager)."""
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: Optional[UUID]) -> None:
    _current_tenant_id.set(tenant_id)


@contextmanager
def tenant_context(tenant_id: UUID):
    """Explicitly scope a block of code to a tenant outside the request cycle.

    Usage:
        with tenant_context(org.id):
            Customer.objects.create(name="...")  # tenant_id auto-populated

    Required for management commands, Celery tasks, and shell sessions —
    anywhere TenantContextMiddleware doesn't run. Does NOT issue the Postgres
    `SET LOCAL`; callers needing RLS enforcement outside the request cycle
    should use `apps.core.db.tenant_scoped_connection` instead, which wraps
    this and the SQL session var together.
    """
    token = _current_tenant_id.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant_id.reset(token)
