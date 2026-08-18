from rest_framework.routers import DefaultRouter

from apps.documents.views import DocumentViewSet

app_name = "documents"

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls
