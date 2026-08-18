from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "email", "data_source", "is_archived", "created_at")
    list_filter = ("data_source", "is_archived")
    search_fields = ("name", "email", "phone")
    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request):
        # Admin is cross-tenant support tooling; TenantScopedManager would
        # raise with no request-scoped tenant context, so use .unscoped()
        # explicitly and rely on Django admin's own staff-only gating.
        return Customer.objects.unscoped()
