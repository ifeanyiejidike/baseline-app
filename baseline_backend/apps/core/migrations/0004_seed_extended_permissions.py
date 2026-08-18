"""
Extends the RBAC catalog seeded in 0003_seed_rbac.py with permissions for
the Documents and Analytics modules, now that both are built. Notifications
is deliberately absent — see apps/notifications/views.py's docstring on why
it's gated by `recipient=request.user` rather than RBAC.
"""
from django.db import migrations

NEW_PERMISSIONS = [
    ("documents", "create"),
    ("documents", "delete"),
    ("analytics", "view"),
]

NEW_ROLE_GRANTS = {
    "owner": ["documents:create", "documents:delete", "analytics:view"],
    "admin": ["documents:create", "documents:delete", "analytics:view"],
    "manager": ["documents:create", "documents:delete", "analytics:view"],
    "member": ["documents:create"],  # members can upload but not delete others' documents
    "viewer": [],
}


def seed_extended_permissions(apps, schema_editor):
    Permission = apps.get_model("core", "Permission")
    RolePermission = apps.get_model("core", "RolePermission")

    codename_to_permission = {}
    for resource, action in NEW_PERMISSIONS:
        permission = Permission.objects.create(
            resource=resource, action=action, codename=f"{resource}:{action}"
        )
        codename_to_permission[permission.codename] = permission

    for role, codenames in NEW_ROLE_GRANTS.items():
        for codename in codenames:
            RolePermission.objects.create(role=role, permission=codename_to_permission[codename])


def unseed_extended_permissions(apps, schema_editor):
    Permission = apps.get_model("core", "Permission")
    RolePermission = apps.get_model("core", "RolePermission")
    codenames = [f"{r}:{a}" for r, a in NEW_PERMISSIONS]
    RolePermission.objects.filter(permission__codename__in=codenames).delete()
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_seed_rbac"),
    ]

    operations = [
        migrations.RunPython(seed_extended_permissions, reverse_code=unseed_extended_permissions),
    ]
