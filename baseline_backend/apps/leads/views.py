from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.audit import record as audit_record
from apps.core.permissions import RequirePermission
from apps.customers.models import Customer
from apps.customers.serializers import CustomerSerializer
from apps.leads.models import Lead
from apps.leads.serializers import LeadConvertSerializer, LeadSerializer


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "data_source"]
    search_fields = ["name", "company_name", "email"]

    def get_queryset(self):
        return Lead.objects.all().order_by("-created_at")

    def get_permissions(self):
        action_permission_map = {
            "create": "leads:create",
            "update": "leads:update",
            "partial_update": "leads:update",
            "destroy": "leads:delete",
            "convert": "leads:convert",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_record(action="lead.created", resource_type="Lead", resource_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_record(
            action="lead.updated",
            resource_type="Lead",
            resource_id=instance.id,
            diff={"changed_fields": list(serializer.validated_data.keys())},
        )

    def perform_destroy(self, instance):
        resource_id = instance.id
        instance.delete()
        audit_record(action="lead.deleted", resource_type="Lead", resource_id=resource_id)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """POST /api/v1/leads/{id}/convert/ — body: {"customer_id": "<uuid>"} (optional)."""
        lead = self.get_object()
        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_id = serializer.validated_data.get("customer_id")
        existing_customer = Customer.objects.get(id=customer_id) if customer_id else None

        try:
            customer = lead.convert(customer=existing_customer)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        audit_record(
            action="lead.converted",
            resource_type="Lead",
            resource_id=lead.id,
            diff={"customer_id": str(customer.id), "linked_existing": existing_customer is not None},
        )
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)
