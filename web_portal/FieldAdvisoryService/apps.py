from django.apps import AppConfig


class FieldadvisoryserviceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FieldAdvisoryService'
    
    def ready(self):
        import FieldAdvisoryService.signals  # noqa: F401

