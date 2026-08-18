from rest_framework.routers import DefaultRouter

from apps.invoices.views import InvoiceViewSet

app_name = "invoices"

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
