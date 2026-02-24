from django.apps import AppConfig


class MainConfig(AppConfig):
    """
    The main app config
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.main"
