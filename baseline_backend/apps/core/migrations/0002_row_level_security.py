"""
Row-Level Security policies — the database-layer backstop for tenant
isolation described throughout the project context (Section 2/7) and in
apps/core/managers.py's module docstring. TenantScopedManager (the ORM
layer) is the primary defense; this migration is what still protects tenant
data if that layer is ever bypassed — raw SQL, the Django admin on an
unscoped queryset, a buggy management command, human error in a one-off
shell session.

How it works:
  - `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` turns on RLS for the table.
  - `... FORCE ROW LEVEL SECURITY` makes it apply even to the table owner
    (the role migrations run as) — without FORCE, the owning role silently
    bypasses RLS, which would make this migration a no-op for the same DB
    user the app connects as in a typical single-role setup. Only an actual
    Postgres superuser or a role with BYPASSRLS still bypasses FORCE; the
    app's runtime DB role should be neither in production.
  - The policy predicate compares `organization_id` against
    `current_setting('app.tenant_id', true)`, which is set per-transaction
    by `apps.core.db.set_rls_tenant()` (called from TenantContextMiddleware
    and `tenant_scoped_connection()`). The `true` argument to
    `current_setting` makes it return NULL instead of raising when unset,
    so a connection with no tenant context set sees zero rows rather than
    erroring — fail-closed, not fail-open.

core_audit_log gets an additional trigger enforcing append-only at the DB
level, independent of which role executes the UPDATE/DELETE — see
AuditLog's model docstring for why this exists on top of the ORM-level
block in AuditLogQuerySet.
"""
from django.db import migrations

TENANT_SCOPED_TABLES = [
    "core_membership",
    "core_invitation",
    "core_audit_log",
    "customers_customer",
    "leads_lead",
    "projects_project",
    "projects_task",
    "invoices_invoice",
    "billing_entitlement",
]


def _enable_rls_sql(table: str) -> str:
    return f"""
        ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON {table}
            USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
    """


def _disable_rls_sql(table: str) -> str:
    return f"""
        DROP POLICY IF EXISTS tenant_isolation ON {table};
        ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
    """


AUDIT_LOG_TRIGGER_UP = """
    CREATE OR REPLACE FUNCTION core_audit_log_immutable() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'core_audit_log is append-only: UPDATE and DELETE are not permitted';
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_core_audit_log_immutable
    BEFORE UPDATE OR DELETE ON core_audit_log
    FOR EACH ROW EXECUTE FUNCTION core_audit_log_immutable();
"""

AUDIT_LOG_TRIGGER_DOWN = """
    DROP TRIGGER IF EXISTS trg_core_audit_log_immutable ON core_audit_log;
    DROP FUNCTION IF EXISTS core_audit_log_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("customers", "0001_initial"),
        ("leads", "0001_initial"),
        ("projects", "0001_initial"),
        ("invoices", "0001_initial"),
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=_enable_rls_sql(table), reverse_sql=_disable_rls_sql(table))
        for table in TENANT_SCOPED_TABLES
    ] + [
        migrations.RunSQL(sql=AUDIT_LOG_TRIGGER_UP, reverse_sql=AUDIT_LOG_TRIGGER_DOWN),
    ]
