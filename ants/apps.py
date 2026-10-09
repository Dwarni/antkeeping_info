from django.apps import AppConfig


class AntsConfig(AppConfig):
    name = "ants"

    def ready(self):
        import ants.signals  # noqa: F401
