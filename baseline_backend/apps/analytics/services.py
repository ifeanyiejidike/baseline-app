"""
AnalyticsService — read-only aggregation over Customers/Leads/Projects/
Invoices/Tasks. Every query here goes through each model's normal
TenantScopedManager (`Model.objects`), so tenant isolation is inherited for
free — this module adds zero new isolation surface area, which is exactly
why Analytics was safe to defer until the core loop existed (project
context Section 1) and safe to build now that it does.

Each method returns a plain dict (JSON-serializable) rather than a
dataclass/model instance — this is a reporting layer, not a domain layer;
there's no behavior to attach, only numbers.
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.leads.models import Lead
from apps.projects.models import Project, Task


class AnalyticsService:
    @staticmethod
    def lead_pipeline_summary() -> dict:
        counts = Lead.objects.values("status").annotate(count=Count("id"))
        by_status = {row["status"]: row["count"] for row in counts}
        total = sum(by_status.values())
        converted = by_status.get(Lead.Status.CONVERTED, 0)
        return {
            "by_status": by_status,
            "total": total,
            "conversion_rate": round(converted / total, 4) if total else None,
        }

    @staticmethod
    def customer_summary() -> dict:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return {
            "total": Customer.objects.filter(is_archived=False).count(),
            "new_last_30_days": Customer.objects.filter(created_at__gte=thirty_days_ago).count(),
            "archived": Customer.objects.filter(is_archived=True).count(),
        }

    @staticmethod
    def project_summary() -> dict:
        counts = Project.objects.values("status").annotate(count=Count("id"))
        return {"by_status": {row["status"]: row["count"] for row in counts}}

    @staticmethod
    def task_summary() -> dict:
        today = timezone.now().date()
        open_statuses = [Task.Status.TODO, Task.Status.IN_PROGRESS]
        return {
            "open": Task.objects.filter(status__in=open_statuses).count(),
            "overdue": Task.objects.filter(status__in=open_statuses, due_date__lt=today).count(),
            "completed_last_30_days": Task.objects.filter(
                status=Task.Status.DONE, completed_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
        }

    @staticmethod
    def revenue_summary() -> dict:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        today = timezone.now().date()

        paid_last_30_days = Invoice.objects.filter(
            status=Invoice.Status.PAID, paid_at__gte=thirty_days_ago
        ).aggregate(total=Sum("total"))["total"] or 0

        outstanding = Invoice.objects.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.OVERDUE]
        ).aggregate(total=Sum("total"))["total"] or 0

        overdue_qs = Invoice.objects.filter(
            Q(status=Invoice.Status.OVERDUE) | Q(status=Invoice.Status.SENT, due_date__lt=today)
        )
        overdue_total = overdue_qs.aggregate(total=Sum("total"))["total"] or 0

        return {
            "paid_last_30_days": str(paid_last_30_days),
            "outstanding_total": str(outstanding),
            "overdue_total": str(overdue_total),
            "overdue_count": overdue_qs.count(),
        }

    @classmethod
    def dashboard_summary(cls) -> dict:
        return {
            "leads": cls.lead_pipeline_summary(),
            "customers": cls.customer_summary(),
            "projects": cls.project_summary(),
            "tasks": cls.task_summary(),
            "revenue": cls.revenue_summary(),
            "generated_at": timezone.now().isoformat(),
        }
