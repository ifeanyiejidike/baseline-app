from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.leads.urls")),
    path("api/v1/", include("apps.projects.urls")),
    path("api/v1/", include("apps.invoices.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.analytics.urls")),
    path("api/v1/billing/", include("apps.billing.urls")),
    path("api/v1/platform-admin/", include("apps.platform_admin.urls")),
]

if settings.DEBUG:
    # Local dev only — in production, media is served by the storage
    # backend/CDN directly, never by Django.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
