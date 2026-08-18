from rest_framework import serializers

from apps.customers.models import Customer
from apps.leads.models import Lead


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "company_name",
            "email",
            "phone",
            "status",
            "data_source",
            "consent_obtained_at",
            "converted_customer",
            "converted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "converted_customer", "converted_at", "created_at", "updated_at"]

    def validate(self, attrs):
        data_source = attrs.get("data_source", getattr(self.instance, "data_source", Lead.DataSource.DIRECT))
        consent_obtained_at = attrs.get(
            "consent_obtained_at", getattr(self.instance, "consent_obtained_at", None)
        )
        if data_source != Lead.DataSource.DIRECT and consent_obtained_at is None:
            raise serializers.ValidationError(
                {"consent_obtained_at": "Required when data_source is not 'direct' (NDPA consent tracking)."}
            )
        return attrs


class LeadConvertSerializer(serializers.Serializer):
    """Body for POST /leads/{id}/convert/. Either link to an existing
    Customer (upsell/expansion case) or omit `customer_id` to create a new
    Customer from the Lead's own data."""

    customer_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_customer_id(self, value):
        if value is None:
            return value
        if not Customer.objects.filter(id=value).exists():
            raise serializers.ValidationError("No customer with that id exists in this organization.")
        return value
