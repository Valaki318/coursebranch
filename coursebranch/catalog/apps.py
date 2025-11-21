from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"

    def ready(self):
        from .models import University, College

        try:
            if not University.objects.exists():
                u = University.objects.create(name="Default University", location="Earth")
                College.objects.create(name="Default College", university=u)
                print("✓ Created default University + College")
        except (OperationalError, ProgrammingError):
            # Database not ready on first migrate
            pass
