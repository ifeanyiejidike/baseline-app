from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Deliberately no RBAC gate beyond IsAuthenticated: a Notification is
    inherently personal to its recipient, not a role-gated resource, so
    every role can read/mark-read their own — the `recipient=request.user`
    filter below (on top of the standard tenant filter) is what actually
    scopes access, not a permission class."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_read", "notification_type"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        from django.utils import timezone

        updated = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"marked_read": updated})
