from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.core.audit import record as audit_record
from apps.core.permissions import RequirePermission
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    filterset_fields = ["customer", "project", "invoice"]
    http_method_names = ["get", "post", "delete", "head", "options"]  # no update — replace via delete+re-upload

    def get_queryset(self):
        return Document.objects.all().select_related("uploaded_by").order_by("-created_at")

    def get_serializer_class(self):
        return DocumentUploadSerializer if self.action == "create" else DocumentSerializer

    def get_permissions(self):
        action_permission_map = {
            "create": "documents:create",
            "destroy": "documents:delete",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_record(
            action="document.uploaded",
            resource_type="Document",
            resource_id=instance.id,
            diff={"owner_type": type(instance.owner).__name__, "filename": instance.original_filename},
        )

    def perform_destroy(self, instance):
        resource_id = instance.id
        filename = instance.original_filename
        # Deletes the DB row AND the underlying file from storage (FileField's
        # storage backend .delete() is NOT automatic on model delete in
        # Django — must be called explicitly or the file becomes an orphan).
        instance.file.delete(save=False)
        instance.delete()
        audit_record(
            action="document.deleted", resource_type="Document", resource_id=resource_id, diff={"filename": filename}
        )
