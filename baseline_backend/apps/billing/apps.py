from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.billing"
    label = "billing"

    def ready(self):
        import apps.billing.signals  # noqa: F401 — registers the post_save receiver
