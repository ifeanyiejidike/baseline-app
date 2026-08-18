"""
Central audit logging.

AuditLog writes go through `record()` in this module exclusively — never
`AuditLog.objects.create(...)` directly from view/service code — so the
actor/IP/user-agent attribution is always populated consistently and the
call site can't forget a field. This is the same "one centralized path,
never scattered inline" principle the project context applies to RBAC checks
and entitlement checks (Section 8).
"""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Optional
from uuid import UUID

_audit_user_id: ContextVar[Optional[UUID]] = ContextVar("audit_user_id", default=None)
_audit_ip: ContextVar[str] = ContextVar("audit_ip", default="")
_audit_user_agent: ContextVar[str] = ContextVar("audit_user_agent", default="")


def set_audit_actor(user_id: Optional[UUID], ip_address: str, user_agent: str) -> None:
    _audit_user_id.set(user_id)
    _audit_ip.set(ip_address)
    _audit_user_agent.set(user_agent)


def clear_audit_actor() -> None:
    _audit_user_id.set(None)
    _audit_ip.set("")
    _audit_user_agent.set("")


@contextmanager
def audit_actor(user_id: Optional[UUID], ip_address: str = "", user_agent: str = ""):
    """Explicit actor context for management commands/Celery tasks, mirroring
    apps.core.context.tenant_context for the audit-attribution concern."""
    set_audit_actor(user_id, ip_address, user_agent)
    try:
        yield
    finally:
        clear_audit_actor()


def record(
    *,
    action: str,
    resource_type: str,
    resource_id: Any,
    diff: Optional[dict] = None,
) -> "AuditLog":  # noqa: F821 — forward ref, avoids circular import at module load
    """Write one AuditLog row for the current tenant + current actor context.

    Args:
        action: short verb, e.g. "customer.created", "invoice.voided",
            "membership.role_changed". Use `resource_type.verb` convention
            so entries are greppable/filterable by resource.
        resource_type: model name the action applies to, e.g. "Customer".
        resource_id: primary key of the affected resource.
        diff: optional before/after field diff for update actions. Must not
            contain raw PII beyond what's already elsewhere in the audit
            trail's blast radius — callers are responsible for redacting
            sensitive field values (e.g. don't diff a password field).
    """
    from apps.core.context import get_current_tenant_id
    from apps.core.models import AuditLog

    return AuditLog.objects.create(
        organization_id=get_current_tenant_id(),
        actor_id=_audit_user_id.get(),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        diff=diff or {},
        ip_address=_audit_ip.get() or None,
        user_agent=_audit_user_agent.get(),
    )
