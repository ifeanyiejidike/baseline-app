from django.contrib import admin

from apps.projects.models import Project, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ("title", "status", "priority", "assigned_to", "due_date")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "customer", "status", "due_date")
    list_filter = ("status",)
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [TaskInline]

    def get_queryset(self, request):
        return Project.objects.unscoped()


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "project", "status", "priority", "assigned_to", "due_date")
    list_filter = ("status", "priority")
    search_fields = ("title",)
    readonly_fields = ("id", "completed_at", "created_at", "updated_at")

    def get_queryset(self, request):
        return Task.objects.unscoped()
