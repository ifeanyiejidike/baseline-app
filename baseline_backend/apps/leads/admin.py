from django.contrib import admin

from apps.leads.models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "data_source", "converted_customer", "created_at")
    list_filter = ("status", "data_source")
    search_fields = ("name", "company_name", "email")
    readonly_fields = ("id", "converted_at", "created_at", "updated_at")

    def get_queryset(self, request):
        return Lead.objects.unscoped()
