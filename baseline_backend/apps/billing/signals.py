"""
Auto-provisions a trial Entitlement whenever a new Organization is created.

Why this exists: once EntitlementService.assert_can_add_seat() /
assert_can_add_project() are actually wired into the enforcement path
(apps/core/views.py, apps/projects/views.py), every org needs SOME active
Entitlement or literally nothing can be created in a brand-new
organization — there's no admin action, no first invite, no first project.
Rather than special-case "no entitlement yet" logic into every call site
that checks limits, every Organization gets a real (if minimal) trial
Entitlement the moment it's created. Upgrading/downgrading later goes
through the normal webhook-driven path in apps/billing/webhooks.py, which
already cancels the previous active Entitlement before creating the new
one — so this trial row gets superseded the same way any other plan change
works, not through special-cased trial-specific logic.

Uses `Entitlement.objects.create(organization=instance, ...)` directly
rather than requiring tenant context: TenantScopedModel.save() only
auto-populates organization_id from the context when it ISN'T already
explicitly provided (see apps/core/managers.py), so passing `organization=`
here sidesteps the chicken-and-egg problem of needing tenant context to
create the very row that tenant context depends on existing.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import Organization

logger = logging.getLogger(__name__)

TRIAL_PLAN_CODE = "trial"


@receiver(post_save, sender=Organization)
def provision_trial_entitlement(sender, instance: Organization, created: bool, **kwargs) -> None:
    if not created:
        return

    from apps.billing.models import Entitlement, Plan

    trial_plan = Plan.objects.filter(code=TRIAL_PLAN_CODE, is_active=True).first()
    if trial_plan is None:
        # Should only happen if this runs before the trial-plan seed
        # migration (apps/billing/migrations/0003_seed_trial_plan.py) has
        # applied — e.g. a fixture loading Organizations mid-migration.
        # Fail loudly in logs rather than silently leaving the org with no
        # entitlement, since that would surface later as a confusing
        # PermissionDenied on the org's very first action instead of here,
        # at the moment the actual cause occurred.
        logger.error(
            "No active 'trial' Plan found — Organization %s was created with "
            "no Entitlement. Run migrations, then provision one manually via "
            "the admin or shell.",
            instance.id,
        )
        return

    Entitlement.objects.create(
        organization=instance,
        plan=trial_plan,
        status=Entitlement.Status.ACTIVE,
        provider=Entitlement.Provider.NONE,
    )
