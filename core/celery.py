import os
import structlog

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

logger = structlog.get_logger(__name__)

app = Celery("cryptotracker")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Configuration de retry par défaut pour toutes les tâches
app.conf.update(
    task_default_retry_delay=60,  # 60 secondes entre retries
    task_max_retries=3,  # Maximum 3 retries
    task_time_limit=30,  # Timeout de 30 secondes par tâche
    task_soft_time_limit=25,  # Soft timeout pour permettre le cleanup
)

# Les tâches sont dans <app>/interfaces/tasks.py, donc hors de l'autodécouverte
app.autodiscover_tasks(["payment.interfaces"], related_name="tasks")

# Surveiller les échecs de tâches
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
