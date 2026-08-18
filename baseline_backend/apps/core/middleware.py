"""
Request-lifecycle middleware for tenant isolation and audit attribution.

TenantContextMiddleware is the most security-critical piece of code in this
codebase: every tenant-scoped query in the request depends on it running
correctly, in order, before any view code executes.
"""
import logging
import uuid

from django.db import transaction
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.context import set_current_tenant_id
from apps.core.db import clear_rls_tenant, set_rls_tenant

logger = logging.getLogger(__name__)

# Endpoints that legitimately run with no tenant context: auth (login,
# refresh, invitation acceptance before membership exists), health checks,
# and the schema/docs endpoints. Every other path requires a resolved
# Membership or the request is rejected before reaching the view.
TENANT_EXEMPT_PATH_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/invitations/accept/",
    "/api/v1/billing/webhooks/",
    "/health/",
    "/admin/",  # Django admin has its own auth; platform_admin views set
    # tenant context explicitly per-view where needed instead of relying on
    # this middleware, since staff frequently need cross-tenant visibility.
    "/api/schema/",
    "/api/docs/",
)


class TenantContextMiddleware(MiddlewareMixin):
    """Resolves the active tenant for the request and sets both enforcement
    layers (ORM contextvar + Postgres RLS session var) before the view runs.

    Resolution order (per project context Section 4 — "never trust a token's
    org claim without a DB check"):
      1. Request must be authenticated (AuthenticationMiddleware already ran).
      2. `X-Organization-Id` header (or `org` claim already validated at auth
         time — see apps.accounts.authentication) identifies the *requested*
         active workspace.
      3. That org_id is re-validated against a live, active Membership row
         in the database on every single request — a previously-valid but
         now-revoked Membership fails here even with a still-unexpired JWT.

    On success: wraps the rest of the request in `transaction.atomic()` and
    issues `SET LOCAL app.tenant_id`, so RLS is active for every query the
    view makes, then clears both on the way out regardless of outcome.
    """

    def process_request(self, request):
        if self._is_exempt(request.path):
            return None

        if not request.user or not request.user.is_authenticated:
            return None  # let DRF's authentication/permission classes reject it

        org_id_header = request.headers.get("X-Organization-Id")
        if not org_id_header:
            return JsonResponse(
                {"detail": "X-Organization-Id header is required."}, status=400
            )

        try:
            org_id = uuid.UUID(org_id_header)
        except (ValueError, AttributeError):
            return JsonResponse({"detail": "X-Organization-Id is not a valid UUID."}, status=400)

        # Local import to avoid a circular import at module load time
        # (models -> managers -> context, middleware -> models).
        from apps.core.models import Membership

        membership = (
            Membership.objects.unscoped()
            .filter(
                user_id=request.user.id,
                organization_id=org_id,
                status=Membership.Status.ACTIVE,
            )
            .select_related("organization")
            .first()
        )
        if membership is None:
            logger.warning(
                "Tenant resolution denied: user=%s requested org=%s with no "
                "active membership.",
                request.user.id,
                org_id,
            )
            return JsonResponse(
                {"detail": "You do not have an active membership in this organization."},
                status=403,
            )

        if membership.organization.is_suspended:
            return JsonResponse({"detail": "This organization is suspended."}, status=403)

        request.membership = membership
        request.organization = membership.organization

        self._atomic_ctx = transaction.atomic()
        self._atomic_ctx.__enter__()
        set_current_tenant_id(org_id)
        set_rls_tenant(org_id)
        return None

    def process_response(self, request, response):
        atomic_ctx = getattr(self, "_atomic_ctx", None)
        if atomic_ctx is not None:
            clear_rls_tenant()
            set_current_tenant_id(None)
            atomic_ctx.__exit__(None, None, None)
            self._atomic_ctx = None
        return response

    def process_exception(self, request, exception):
        atomic_ctx = getattr(self, "_atomic_ctx", None)
        if atomic_ctx is not None:
            clear_rls_tenant()
            set_current_tenant_id(None)
            atomic_ctx.__exit__(type(exception), exception, exception.__traceback__)
            self._atomic_ctx = None
        return None

    @staticmethod
    def _is_exempt(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in TENANT_EXEMPT_PATH_PREFIXES)


class AuditContextMiddleware(MiddlewareMixin):
    """Stashes the acting user + request IP/UA into a contextvar so
    AuditLog entries created deep in a service call (not just at the view
    layer) can be attributed without threading `request` through every
    function signature. Pure attribution metadata — carries no
    authorization weight, unlike TenantContextMiddleware's tenant_id.
    """

    def process_request(self, request):
        from apps.core.audit import set_audit_actor

        set_audit_actor(
            user_id=getattr(request.user, "id", None) if request.user.is_authenticated else None,
            ip_address=self._client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:512],
        )
        return None

    def process_response(self, request, response):
        from apps.core.audit import clear_audit_actor

        clear_audit_actor()
        return response

    @staticmethod
    def _client_ip(request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
