from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.audit import record as audit_record
from apps.core.permissions import RequirePermission
from apps.projects.models import Project, Task
from apps.projects.serializers import ProjectDetailSerializer, ProjectSerializer, TaskSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "customer"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return Project.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.action == "retrieve" else ProjectSerializer

    def get_permissions(self):
        action_permission_map = {
            "create": "projects:create",
            "update": "projects:update",
            "partial_update": "projects:update",
            "destroy": "projects:delete",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        from apps.billing.services import EntitlementService

        EntitlementService.assert_can_add_project()
        instance = serializer.save()
        audit_record(action="project.created", resource_type="Project", resource_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_record(
            action="project.updated",
            resource_type="Project",
            resource_id=instance.id,
            diff={"changed_fields": list(serializer.validated_data.keys())},
        )

    def perform_destroy(self, instance):
        resource_id = instance.id
        instance.delete()
        audit_record(action="project.deleted", resource_type="Project", resource_id=resource_id)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority", "project", "assigned_to"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        return Task.objects.all().order_by("-created_at")

    def get_permissions(self):
        action_permission_map = {
            "create": "tasks:create",
            "update": "tasks:update",
            "partial_update": "tasks:update",
            "destroy": "tasks:delete",
        }
        codename = action_permission_map.get(self.action)
        if codename:
            return [IsAuthenticated(), RequirePermission(codename)]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_record(action="task.created", resource_type="Task", resource_id=instance.id)
        self._notify_assignee_if_set(instance)

    def perform_update(self, serializer):
        previous_assignee_id = serializer.instance.assigned_to_id
        instance = serializer.save()
        audit_record(
            action="task.updated",
            resource_type="Task",
            resource_id=instance.id,
            diff={"changed_fields": list(serializer.validated_data.keys())},
        )
        if instance.assigned_to_id and instance.assigned_to_id != previous_assignee_id:
            self._notify_assignee_if_set(instance)

    @staticmethod
    def _notify_assignee_if_set(task) -> None:
        if task.assigned_to_id is None:
            return
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify(
            recipient=task.assigned_to,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            title=f"You were assigned: {task.title}",
            resource_type="Task",
            resource_id=task.id,
        )

    def perform_destroy(self, instance):
        resource_id = instance.id
        instance.delete()
        audit_record(action="task.deleted", resource_type="Task", resource_id=resource_id)
