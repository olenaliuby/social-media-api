from django.apps import AppConfig


class CoreSocialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core_social"

    def ready(self):
        import core_social.signals
