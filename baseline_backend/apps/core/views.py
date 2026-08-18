from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import record as audit_record
from apps.core.models import Invitation, Membership
from apps.core.permissions import RequirePermission
from apps.core.serializers import InvitationAcceptSerializer, InvitationSerializer, MembershipSerializer


class MembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only: Memberships are created via invitation-acceptance, and role
    changes/removal go through dedicated actions below (not generic PATCH),
    since both need the "can't remove the last Owner" guard from
    Membership.is_last_owner()."""

    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Membership.objects.all().select_related("user").order_by("-created_at")


class InvitationViewSet(viewsets.ModelViewSet):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]  # no update — invites are immutable once sent

    def get_queryset(self):
        return Invitation.objects.all().order_by("-created_at")

    def get_permissions(self):
        action_permission_map = {
            "create": "invitations:create",
            "destroy": "invitations:revoke",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        from apps.billing.services import EntitlementService

        # Fail-fast check: if the org is already at its seat limit, don't
        # let an invite go out that can never be accepted. This is a UX
        # convenience, not the authoritative enforcement point — a seat
        # isn't actually consumed until acceptance (see
        # InvitationAcceptView below), since an org could have another
        # member leave in the meantime.
        EntitlementService.assert_can_add_seat()
        instance = serializer.save(invited_by=self.request.user)
        audit_record(action="invitation.created", resource_type="Invitation", resource_id=instance.id)
        # Email dispatch intentionally omitted: no transactional email
        # provider is confirmed yet (project context Section 3a). Wiring
        # this send is a one-line addition once EMAIL_BACKEND points at a
        # real provider — the Invitation row + token already exist as the
        # source of truth regardless of whether the email sends.

    def perform_destroy(self, instance):
        resource_id = instance.id
        instance.status = Invitation.Status.REVOKED
        instance.save(update_fields=["status", "updated_at"])
        audit_record(action="invitation.revoked", resource_type="Invitation", resource_id=resource_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationAcceptView(APIView):
    """POST /api/v1/invitations/accept/ — body: {"token": "..."}

    Deliberately outside tenant/membership requirements (no Membership
    exists yet for this user in this org — that's exactly what this
    endpoint creates), which is why it's listed in
    TenantContextMiddleware.TENANT_EXEMPT_PATH_PREFIXES.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        invitation = Invitation.objects.unscoped().filter(token=token).first()
        if invitation is None:
            return Response({"detail": "Invalid invitation token."}, status=status.HTTP_404_NOT_FOUND)
        if invitation.status != Invitation.Status.PENDING:
            return Response({"detail": f"Invitation is {invitation.status}."}, status=status.HTTP_400_BAD_REQUEST)
        if invitation.is_expired:
            invitation.status = Invitation.Status.EXPIRED
            invitation.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Invitation has expired."}, status=status.HTTP_400_BAD_REQUEST)
        if invitation.email.lower() != request.user.email.lower():
            return Response(
                {"detail": "This invitation was sent to a different email address."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.billing.services import EntitlementService
        from apps.core.db import tenant_scoped_connection
        from django.core.exceptions import PermissionDenied

        with tenant_scoped_connection(invitation.organization_id), transaction.atomic():
            # Authoritative seat-limit check: this, not the fail-fast check
            # in InvitationViewSet.perform_create, is what actually decides
            # whether a seat gets consumed — an org's seat count can change
            # between an invite being sent and accepted (another member
            # could leave, or the org could downgrade its plan).
            try:
                EntitlementService.assert_can_add_seat()
            except PermissionDenied as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

            membership, created = Membership.objects.unscoped().get_or_create(
                organization_id=invitation.organization_id,
                user=request.user,
                defaults={"role": invitation.role, "status": Membership.Status.ACTIVE, "joined_at": timezone.now()},
            )
            if not created:
                return Response({"detail": "You are already a member of this organization."}, status=400)

            invitation.status = Invitation.Status.ACCEPTED
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["status", "accepted_at", "updated_at"])

            audit_record(action="membership.created", resource_type="Membership", resource_id=membership.id)
            if invitation.invited_by_id:
                from apps.notifications.models import Notification
                from apps.notifications.services import NotificationService

                NotificationService.notify(
                    recipient=invitation.invited_by,
                    notification_type=Notification.NotificationType.MEMBER_INVITED,
                    title=f"{invitation.email} accepted your invitation",
                    resource_type="Membership",
                    resource_id=membership.id,
                )

        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
