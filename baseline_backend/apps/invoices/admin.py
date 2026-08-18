from django.contrib import admin

from apps.invoices.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "organization", "customer", "status", "total", "due_date")
    list_filter = ("status", "currency")
    search_fields = ("invoice_number", "customer__name")
    readonly_fields = ("id", "invoice_number", "total", "paid_at", "created_at", "updated_at")

    def get_queryset(self, request):
        return Invoice.objects.unscoped()

    def has_delete_permission(self, request, obj=None):
        # Mirrors the API: invoices are financial records, void not delete.
        return False
