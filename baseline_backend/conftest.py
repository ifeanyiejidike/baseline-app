import pytest

from apps.core.db import tenant_scoped_connection


@pytest.fixture
def org_factory(db):
    from apps.core.models import Organization

    def make(name="Acme Inc", slug=None):
        return Organization.objects.create(name=name, slug=slug or name.lower().replace(" ", "-"))

    return make


@pytest.fixture
def user_factory(db):
    from apps.accounts.models import User

    def make(email="user@example.com", password="a-very-secure-pw-123"):  # noqa: S106 test fixture
        return User.objects.create_user(email=email, password=password)

    return make


@pytest.fixture
def membership_factory(db):
    from apps.core.models import Membership

    def make(organization, user, role=Membership.Role.MEMBER, status=Membership.Status.ACTIVE):
        with tenant_scoped_connection(organization.id):
            return Membership.objects.create(
                organization=organization, user=user, role=role, status=status
            )

    return make


@pytest.fixture
def as_tenant():
    """Usage: `with as_tenant(org):` — wraps both the ORM contextvar and the
    Postgres RLS session var, mirroring what a real request does."""
    return tenant_scoped_connection
