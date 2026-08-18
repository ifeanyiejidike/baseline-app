"""
platform_admin holds no models of its own in v1. It's a structural boundary
(project context Section 4 + Section 7 app-list decision): internal
Baseline-staff tooling that legitimately needs cross-tenant visibility,
kept deliberately separate from the tenant-facing RBAC system in `core` so
"is_staff" (platform access) and "Membership.role" (tenant-scoped access)
can never be confused for one another at a call site. Views here gate on
`request.user.is_staff`, never on `RequirePermission`/tenant Membership.
"""
