from django.apps import AppConfig


class FieldadvisoryserviceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FieldAdvisoryService'
    verbose_name = 'Farmer Meeting'
    
    def ready(self):
        import FieldAdvisoryService.signals  # noqa: F401

