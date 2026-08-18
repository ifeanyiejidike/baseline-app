from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self):
        from django.db.models.signals import post_migrate

        def _clear_permission_cache(sender, **kwargs):
            from apps.core.permissions import _role_permission_map

            _role_permission_map.cache_clear()

        post_migrate.connect(_clear_permission_cache, sender=self)
