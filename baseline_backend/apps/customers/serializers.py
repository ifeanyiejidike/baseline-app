from rest_framework import serializers

from apps.customers.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "primary_contact_name",
            "email",
            "phone",
            "billing_address",
            "data_source",
            "consent_obtained_at",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        data_source = attrs.get("data_source", getattr(self.instance, "data_source", Customer.DataSource.DIRECT))
        consent_obtained_at = attrs.get(
            "consent_obtained_at", getattr(self.instance, "consent_obtained_at", None)
        )
        if data_source != Customer.DataSource.DIRECT and consent_obtained_at is None:
            raise serializers.ValidationError(
                {"consent_obtained_at": "Required when data_source is not 'direct' (NDPA consent tracking)."}
            )
        return attrs
