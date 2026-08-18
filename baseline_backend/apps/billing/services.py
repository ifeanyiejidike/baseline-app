"""
EntitlementService — the only sanctioned way to answer "can this
Organization do X." Project context Section 8, explicit "Never happen":
inline `org.plan == 'pro'` checks scattered through the codebase. Every
feature gate, seat/project-limit check, and billing-status gate in the
system calls a method on this service, never reads Entitlement fields
directly from view/service code.
"""
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db.models import Count

from apps.billing.models import Entitlement
from apps.core.context import get_current_tenant_id


@dataclass(frozen=True)
class LimitCheckResult:
    allowed: bool
    current: int
    limit: int | None  # None = unlimited


class EntitlementService:
    @staticmethod
    def get_active_entitlement() -> Entitlement | None:
        tenant_id = get_current_tenant_id()
        return (
            Entitlement.objects.select_related("plan")
            .filter(organization_id=tenant_id, status=Entitlement.Status.ACTIVE)
            .first()
        )

    @classmethod
    def require_active(cls) -> Entitlement:
        """Raises PermissionDenied (-> DRF 403) if the tenant has no active
        entitlement. Call at the top of any view/service gating access to a
        billable feature."""
        entitlement = cls.get_active_entitlement()
        if entitlement is None:
            raise PermissionDenied("This organization has no active subscription.")
        return entitlement

    @classmethod
    def check_seat_limit(cls) -> LimitCheckResult:
        from apps.core.models import Membership

        entitlement = cls.require_active()
        tenant_id = get_current_tenant_id()
        current = Membership.objects.filter(
            organization_id=tenant_id, status=Membership.Status.ACTIVE
        ).count()
        limit = entitlement.plan.seat_limit
        return LimitCheckResult(allowed=(limit is None or current < limit), current=current, limit=limit)

    @classmethod
    def check_project_limit(cls) -> LimitCheckResult:
        from apps.projects.models import Project

        entitlement = cls.require_active()
        current = Project.objects.count()  # already tenant-scoped by TenantScopedManager
        limit = entitlement.plan.project_limit
        return LimitCheckResult(allowed=(limit is None or current < limit), current=current, limit=limit)

    @classmethod
    def assert_can_add_seat(cls) -> None:
        result = cls.check_seat_limit()
        if not result.allowed:
            raise PermissionDenied(
                f"Seat limit reached ({result.current}/{result.limit}). Upgrade your plan to add more members."
            )

    @classmethod
    def assert_can_add_project(cls) -> None:
        result = cls.check_project_limit()
        if not result.allowed:
            raise PermissionDenied(
                f"Project limit reached ({result.current}/{result.limit}). Upgrade your plan to add more projects."
            )
