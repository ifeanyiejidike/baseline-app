from rest_framework import serializers

from apps.core.models import Organization


class OrganizationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "is_suspended", "created_at", "updated_at"]
        read_only_fields = fields
