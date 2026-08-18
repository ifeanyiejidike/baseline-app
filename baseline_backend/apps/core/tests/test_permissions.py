import pytest

from apps.core.models import Membership, Permission, RolePermission
from apps.core.permissions import _role_permission_map, has_permission


@pytest.fixture(autouse=True)
def _clear_permission_cache():
    """The role->permission map is process-cached (see permissions.py); each
    test must start from a clean cache since tests mutate RolePermission."""
    _role_permission_map.cache_clear()
    yield
    _role_permission_map.cache_clear()


@pytest.fixture
def seeded_permissions(db):
    perm = Permission.objects.create(resource="customers", action="delete", codename="customers:delete")
    RolePermission.objects.create(role=Membership.Role.ADMIN, permission=perm)
    return perm


class TestHasPermission:
    def test_role_with_grant_is_allowed(self, seeded_permissions):
        assert has_permission(Membership.Role.ADMIN, "customers:delete") is True

    def test_role_without_grant_is_denied(self, seeded_permissions):
        assert has_permission(Membership.Role.VIEWER, "customers:delete") is False

    def test_unknown_codename_is_denied(self, seeded_permissions):
        assert has_permission(Membership.Role.ADMIN, "nonexistent:action") is False

    def test_unknown_role_is_denied(self, seeded_permissions):
        assert has_permission("not-a-real-role", "customers:delete") is False
