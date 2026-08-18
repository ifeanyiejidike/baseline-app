"""
Auth backend abstraction.

Today this only wraps email+password via Django's ModelBackend. The point of
having `BaselineAuthBackend` as its own class — rather than using
`django.contrib.auth.backends.ModelBackend` directly in AUTHENTICATION_BACKENDS
— is that adding SSO later means adding `SAMLAuthBackend` /
`GoogleSSOAuthBackend` alongside this one, each producing the same `User`
instance via the same `auth_provider` field, without touching call sites
that just do `authenticate(request, email=..., password=...)` or, for SSO,
`authenticate(request, sso_token=...)`.
"""
from django.contrib.auth.backends import ModelBackend

from apps.accounts.models import User


class BaselineAuthBackend(ModelBackend):
    def authenticate(self, request, email: str | None = None, password: str | None = None, **kwargs):
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Run the hasher anyway to keep timing consistent between
            # "user does not exist" and "wrong password" — avoids a
            # user-enumeration timing side-channel.
            User().set_password(password)
            return None

        if user.auth_provider != User.AuthProvider.PASSWORD:
            # SSO-provisioned account attempting password login — reject
            # rather than falling through to a password check against an
            # unusable password hash (which would already fail, but this is
            # explicit about *why*, for clearer logging/error messages).
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
