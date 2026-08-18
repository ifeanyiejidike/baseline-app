from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "recipient", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "recipient__email")
    readonly_fields = ("id", "read_at", "created_at", "updated_at")

    def get_queryset(self, request):
        return Notification.objects.unscoped()
