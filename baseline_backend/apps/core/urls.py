from rest_framework.routers import DefaultRouter

from apps.core.views import InvitationAcceptView, InvitationViewSet, MembershipViewSet
from django.urls import include, path

app_name = "core"

router = DefaultRouter()
router.register("memberships", MembershipViewSet, basename="membership")
router.register("invitations", InvitationViewSet, basename="invitation")

urlpatterns = [
    path("invitations/accept/", InvitationAcceptView.as_view(), name="invitation_accept"),
    path("", include(router.urls)),
]
