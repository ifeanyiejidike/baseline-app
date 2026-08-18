"""
Project — one of the four MVP core-loop modules. Task lives here as a
nested model (project context Section 7 app-list decision), not a
standalone app, since Tasks is explicitly out of MVP scope as its own
module — but a Task needs *some* home for FK purposes, and it belongs
conceptually under Project.

Project<->Customer (confirmed, project context Section 6): OPTIONAL FK.
Baseline explicitly covers internal operations tooling (Section 1), so an
internal project ("Q3 hiring plan") legitimately has no Customer.

Task<->Project (confirmed, project context Section 6): OPTIONAL FK.
Standalone/personal Tasks are allowed (a private to-do, or a quick-capture
item pending triage into a Project). Task carries its own `organization` FK
directly (inherited from TenantScopedModel) so tenant scoping doesn't
depend on the optional Project relationship.
"""
from django.db import models

from apps.core.managers import TenantScopedModel


class Project(TenantScopedModel):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)

    # Optional — internal (non-client) projects have no Customer.
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "projects_project"
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "customer"]),
        ]

    def __str__(self) -> str:
        return self.name


class Task(TenantScopedModel):
    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    # Optional — standalone Tasks (personal / not-yet-triaged) are allowed.
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "projects_task"
        indexes = [
            models.Index(fields=["organization", "project", "status"]),
            models.Index(fields=["organization", "assigned_to", "status"]),
        ]

    def __str__(self) -> str:
        return self.title

    def mark_done(self) -> None:
        from django.utils import timezone

        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])
