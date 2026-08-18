from django.contrib import admin

from apps.billing.models import Entitlement, Plan, WebhookEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price_ngn", "seat_limit", "project_limit", "is_active")
    list_filter = ("is_active",)


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "provider", "current_period_end")
    list_filter = ("status", "provider")
    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request):
        return Entitlement.objects.unscoped()


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_type", "provider_event_id", "processed_at", "received_at")
    list_filter = ("provider", "event_type")
    readonly_fields = [f.name for f in WebhookEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
