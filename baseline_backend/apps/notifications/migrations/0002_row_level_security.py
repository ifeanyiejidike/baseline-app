"""
Row-Level Security for notifications_notification. Same pattern as
apps/core/migrations/0002_row_level_security.py — see that file's docstring
for the full rationale.
"""
from django.db import migrations

TABLE = "notifications_notification"

ENABLE_RLS_SQL = f"""
    ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON {TABLE}
        USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
"""

DISABLE_RLS_SQL = f"""
    DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
    ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_RLS_SQL, reverse_sql=DISABLE_RLS_SQL),
    ]
