import os
import django

# Initialiser Django uniquement si les settings sont configurés
if os.environ.get('DJANGO_SETTINGS_MODULE'):
    if not django.conf.settings.configured:
        django.setup()
    from .server import OrderEngine
    __all__ = ["OrderEngine"]
else:
    __all__ = []
