"""Package racine de la configuration, expose l'app Celery"""

from core.celery import app as celery_app

__all__ = ("celery_app",)
