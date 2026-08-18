from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "organization", "owner", "size_bytes", "uploaded_by", "created_at")
    search_fields = ("original_filename",)
    readonly_fields = ("id", "content_type", "size_bytes", "created_at", "updated_at")

    def get_queryset(self, request):
        return Document.objects.unscoped().select_related("customer", "project", "invoice")
