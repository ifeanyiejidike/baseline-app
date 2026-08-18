from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.audit import record as audit_record
from apps.core.permissions import RequirePermission
from apps.invoices.models import Invoice
from apps.invoices.serializers import InvoiceSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "customer", "project"]
    search_fields = ["invoice_number"]

    def get_queryset(self):
        return Invoice.objects.all().order_by("-created_at")

    def get_permissions(self):
        action_permission_map = {
            "create": "invoices:create",
            "update": "invoices:update",
            "partial_update": "invoices:update",
            "destroy": "invoices:delete",
            "mark_paid": "invoices:update",
            "void": "invoices:void",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_record(action="invoice.created", resource_type="Invoice", resource_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_record(
            action="invoice.updated",
            resource_type="Invoice",
            resource_id=instance.id,
            diff={"changed_fields": list(serializer.validated_data.keys())},
        )

    def destroy(self, request, *args, **kwargs):
        # Invoices are financial records — deletion is deliberately not
        # exposed via DELETE. Use the `void` action instead, which preserves
        # the row for audit/statutory-retention purposes.
        return Response(
            {"detail": "Invoices cannot be deleted. Use the void action instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        invoice.mark_paid()
        audit_record(action="invoice.paid", resource_type="Invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = Invoice.Status.VOID
        invoice.save(update_fields=["status", "updated_at"])
        audit_record(action="invoice.voided", resource_type="Invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data)
