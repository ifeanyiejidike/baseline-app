from decimal import Decimal

from rest_framework import serializers

from apps.invoices.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "customer",
            "project",
            "status",
            "currency",
            "subtotal",
            "tax_amount",
            "total",
            "issued_at",
            "due_date",
            "paid_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "invoice_number", "total", "paid_at", "created_at", "updated_at"]

    def validate_subtotal(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("subtotal cannot be negative.")
        return value

    def validate(self, attrs):
        # Cross-field guard: if a project is set, it must belong to the same
        # customer as the invoice (or have no customer at all — an internal
        # project can still be attached to a client invoice only if that
        # project has no conflicting customer of its own).
        project = attrs.get("project", getattr(self.instance, "project", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if project is not None and project.customer_id not in (None, getattr(customer, "id", None)):
            raise serializers.ValidationError(
                {"project": "This project belongs to a different customer than the invoice."}
            )
        return attrs
