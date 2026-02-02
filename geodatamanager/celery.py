import os
from celery import Celery

import environ

env = environ.Env(DEBUG=(bool,False))
environ.Env.read_env()

environment = env('DEBUG')
if environment:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geodatamanager.settings.dev")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geodatamanager.settings.production")

app = Celery("geodatamanager")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
