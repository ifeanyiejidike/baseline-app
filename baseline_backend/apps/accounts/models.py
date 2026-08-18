"""
Custom User model.

Project context Section 3: "Auth strategy is abstracted from day one — not
hardcoded to email+password — specifically to support SSO/SAML later without
a rewrite." Concretely, that means:

  - User identity is `email`, not a separate `username` field (one less
    thing an SSO-provisioned identity has to fake).
  - `password` is nullable-in-practice-for-SSO: Django's AbstractBaseUser
    already supports `set_unusable_password()` for SSO-only accounts; no
    schema change needed when that's added.
  - `auth_provider` records how the account authenticates. "password" today;
    "google" / "saml:<idp>" etc. later — the column exists now so adding a
    provider is a data migration, not a schema migration.
  - No FK to Organization here: identity is global (one User can hold
    Memberships in multiple Organizations), matching Section 4's confirmed
    many-to-many via Membership.
"""
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class AuthProvider(models.TextChoices):
        PASSWORD = "password", "Email & Password"
        # Placeholders for future SSO providers — adding one is a data
        # migration (allow a new choice value), not a schema change.
        GOOGLE = "google", "Google SSO"
        SAML = "saml", "SAML SSO"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    auth_provider = models.CharField(
        max_length=20, choices=AuthProvider.choices, default=AuthProvider.PASSWORD
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Grants access to the Django admin and platform_admin "
        "tooling — internal Baseline staff only, structurally distinct "
        "from a tenant Membership role (project context Section 4).",
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email
