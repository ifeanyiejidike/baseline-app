from apps.core.context import tenant_context
from apps.customers.models import Customer
from apps.projects.models import Project, Task


class TestOptionalRelationships:
    def test_project_can_exist_without_customer(self, org_factory):
        """Confirmed decision: internal projects have no Customer."""
        org = org_factory()
        with tenant_context(org.id):
            project = Project.objects.create(name="Internal: Q3 hiring plan")
            assert project.customer_id is None

    def test_task_can_exist_without_project(self, org_factory):
        """Confirmed decision: standalone/personal Tasks are allowed."""
        org = org_factory()
        with tenant_context(org.id):
            task = Task.objects.create(title="Buy more coffee")
            assert task.project_id is None
            assert task.organization_id == org.id  # tenant scope independent of Project

    def test_task_inherits_no_implicit_project_scoping(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            project = Project.objects.create(name="Client Website", customer=customer)
            in_project_task = Task.objects.create(title="Build homepage", project=project)
            standalone_task = Task.objects.create(title="Personal reminder")

            all_tasks = set(Task.objects.values_list("title", flat=True))
            assert all_tasks == {"Build homepage", "Personal reminder"}
            assert in_project_task.project_id == project.id
            assert standalone_task.project_id is None
