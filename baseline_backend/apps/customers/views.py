from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.audit import record as audit_record
from apps.core.permissions import RequirePermission
from apps.customers.models import Customer
from apps.customers.serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """Standard CRUD. `get_queryset` needs no explicit tenant filter — it's
    already enforced by TenantScopedManager (`Customer.objects` == the
    tenant-scoped manager), so `Customer.objects.all()` here is safe by
    construction, not despite appearances."""

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_archived", "data_source"]
    search_fields = ["name", "email", "phone"]

    def get_queryset(self):
        return Customer.objects.all().order_by("-created_at")

    def get_permissions(self):
        action_permission_map = {
            "create": "customers:create",
            "update": "customers:update",
            "partial_update": "customers:update",
            "destroy": "customers:delete",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]  # read actions: membership alone is sufficient

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_record(action="customer.created", resource_type="Customer", resource_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_record(
            action="customer.updated",
            resource_type="Customer",
            resource_id=instance.id,
            diff={"changed_fields": list(serializer.validated_data.keys())},
        )

    def perform_destroy(self, instance):
        resource_id = instance.id
        instance.delete()
        audit_record(action="customer.deleted", resource_type="Customer", resource_id=resource_id)
