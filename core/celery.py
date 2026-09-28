import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("cryptotracker")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Les tâches sont dans <app>/interfaces/tasks.py, donc hors de l'autodécouverte
app.autodiscover_tasks(["payment.interfaces"], related_name="tasks")
