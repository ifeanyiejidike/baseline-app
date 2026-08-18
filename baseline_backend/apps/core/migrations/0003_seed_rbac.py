"""
Seeds the Permission catalog and default RolePermission grants.

Grant philosophy, mapped to Membership.Role (project context Section 4):
  - OWNER:   everything, including org-destructive actions (not modeled as
             a distinct permission here since Owner-only checks like "delete
             organization" go through an explicit role check, not RBAC —
             RBAC governs day-to-day resource actions).
  - ADMIN:   everything except billing/entitlement management and inviting
             other Admins/Owners (that asymmetry is enforced in the
             Invitation view layer, not here — RBAC alone can't express
             "can invite at or below my own role").
  - MANAGER: full CRUD on the core-loop resources (customers, leads,
             projects, tasks, invoices) but no invitations, no billing.
  - MEMBER:  create/update on core-loop resources, no delete, no invitations.
  - VIEWER:  read-only everywhere (no explicit grants needed — the RBAC
             layer only gates non-read actions; list/retrieve endpoints
             check IsAuthenticated only, per every ViewSet's get_permissions
             in this codebase).
"""
from django.db import migrations


PERMISSIONS = [
    # (resource, action)
    ("customers", "create"), ("customers", "update"), ("customers", "delete"),
    ("leads", "create"), ("leads", "update"), ("leads", "delete"), ("leads", "convert"),
    ("projects", "create"), ("projects", "update"), ("projects", "delete"),
    ("tasks", "create"), ("tasks", "update"), ("tasks", "delete"),
    ("invoices", "create"), ("invoices", "update"), ("invoices", "void"),
    ("invitations", "create"), ("invitations", "revoke"),
]

ROLE_GRANTS = {
    "owner": [f"{r}:{a}" for r, a in PERMISSIONS],
    "admin": [f"{r}:{a}" for r, a in PERMISSIONS if r not in ("invitations",)]
    + ["invitations:create", "invitations:revoke"],
    "manager": [f"{r}:{a}" for r, a in PERMISSIONS if r != "invitations"],
    "member": [
        "customers:create", "customers:update",
        "leads:create", "leads:update", "leads:convert",
        "projects:create", "projects:update",
        "tasks:create", "tasks:update",
        "invoices:create", "invoices:update",
    ],
    "viewer": [],
}


def seed_rbac(apps, schema_editor):
    Permission = apps.get_model("core", "Permission")
    RolePermission = apps.get_model("core", "RolePermission")

    codename_to_permission = {}
    for resource, action in PERMISSIONS:
        permission = Permission.objects.create(
            resource=resource, action=action, codename=f"{resource}:{action}"
        )
        codename_to_permission[permission.codename] = permission

    for role, codenames in ROLE_GRANTS.items():
        for codename in codenames:
            RolePermission.objects.create(role=role, permission=codename_to_permission[codename])


def unseed_rbac(apps, schema_editor):
    RolePermission = apps.get_model("core", "RolePermission")
    Permission = apps.get_model("core", "Permission")
    RolePermission.objects.all().delete()
    Permission.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_row_level_security"),
    ]

    operations = [
        migrations.RunPython(seed_rbac, reverse_code=unseed_rbac),
    ]
