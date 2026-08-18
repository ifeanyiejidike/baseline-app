from rest_framework import serializers

from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Read/list representation. `file` renders as a URL; upload happens
    through DocumentUploadSerializer instead, which is the only path that
    accepts a raw file plus owner reference together."""

    file_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "customer",
            "project",
            "invoice",
            "file_url",
            "original_filename",
            "content_type",
            "size_bytes",
            "uploaded_by",
            "uploaded_by_email",
            "description",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj: Document) -> str | None:
        request = self.context.get("request")
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Write path. Exactly one of customer/project/invoice must be provided
    — mirrors the model's CheckConstraint at the API validation layer so a
    bad request fails with a clear 400 rather than surfacing as an opaque
    IntegrityError from the database."""

    class Meta:
        model = Document
        fields = ["customer", "project", "invoice", "file", "description"]

    def validate(self, attrs):
        owners = [attrs.get("customer"), attrs.get("project"), attrs.get("invoice")]
        owners_set = sum(1 for owner in owners if owner is not None)
        if owners_set != 1:
            raise serializers.ValidationError(
                "Exactly one of customer, project, or invoice must be set."
            )
        return attrs

    def create(self, validated_data):
        uploaded_file = validated_data["file"]
        validated_data["original_filename"] = uploaded_file.name
        validated_data["content_type"] = getattr(uploaded_file, "content_type", "") or ""
        validated_data["size_bytes"] = uploaded_file.size
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)
