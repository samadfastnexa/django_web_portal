from django.apps import AppConfig


class DocumentManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'document_management'
    verbose_name = 'Document Management'

    def ready(self):
        import document_management.signals  # noqa
