from preferences.models import Setting
from django.contrib.auth import get_user_model

User = get_user_model()

class PreferencesSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def create_settings(self, users):
        """Create sample settings"""
        settings = []
        for i in range(1, 6):
            setting, created = Setting.objects.get_or_create(
                slug=f'setting_{i}',
                defaults={
                    'user': users[i-1] if i > 1 else None,  # First setting is global
                    'value': {
                        'theme': f'theme_{i}',
                        'language': 'en',
                        'notifications': True,
                        'setting_value': f'value_{i}'
                    }
                }
            )
            settings.append(setting)
        if self.stdout:
            self.stdout.write(f'Created {len(settings)} settings')
        return settings