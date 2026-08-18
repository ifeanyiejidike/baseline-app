"""
Helpers that pair the Python-side tenant contextvar with the Postgres-side
session variable that Row-Level Security policies check.

`SET LOCAL` scopes the setting to the current transaction only — it is
automatically cleared on COMMIT/ROLLBACK, so there is no risk of it leaking
across requests via a pooled connection.
"""
from contextlib import contextmanager
from uuid import UUID

from django.db import connection

from apps.core.context import tenant_context

RLS_SESSION_VAR = "app.tenant_id"


def set_rls_tenant(tenant_id: UUID) -> None:
    """Issue `SET LOCAL app.tenant_id` for the current transaction.

    Must be called inside a transaction (TenantContextMiddleware wraps each
    request in `transaction.atomic()` specifically so this holds for the
    request's full lifetime). Uses a parameterized query — never string-
    interpolate the tenant_id into SQL.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [RLS_SESSION_VAR, str(tenant_id)])


def clear_rls_tenant() -> None:
    """Reset the RLS session var. Belt-and-braces cleanup; SET LOCAL already
    expires at transaction end, but explicit teardown avoids relying solely
    on that for connections reused outside a clean transaction boundary
    (e.g. a management command that doesn't wrap in atomic())."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, '', true)", [RLS_SESSION_VAR])


@contextmanager
def tenant_scoped_connection(tenant_id: UUID):
    """Scope BOTH the ORM contextvar and the Postgres RLS session var to a
    tenant. Use this (not `tenant_context` alone) for management commands,
    Celery tasks, or shell sessions that need the same double-layer
    enforcement a request gets — e.g. a data-export or hard-delete command
    acting on tenant data.

    Usage:
        with tenant_scoped_connection(org.id):
            Customer.objects.all()  # ORM-filtered AND RLS-filtered
    """
    with tenant_context(tenant_id):
        set_rls_tenant(tenant_id)
        try:
            yield
        finally:
            clear_rls_tenant()
