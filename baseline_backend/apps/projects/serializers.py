from rest_framework import serializers

from apps.projects.models import Project, Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to",
            "due_date",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "completed_at", "created_at", "updated_at"]


class ProjectSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(source="tasks.count", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "status",
            "customer",
            "start_date",
            "due_date",
            "task_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "task_count", "created_at", "updated_at"]


class ProjectDetailSerializer(ProjectSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ["tasks"]
