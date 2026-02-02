"""
WSGI config for geodatamanager project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import logging
import environ
from django.core.wsgi import get_wsgi_application

env = environ.Env(DEBUG=(bool,False))
environ.Env.read_env()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

environment = env('DEBUG')
if not environment:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geodatamanager.settings.production")
    log.info(f" Debug set to {environment}   Running in Production mode")
else:   
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geodatamanager.settings.dev")

    log.info(f"Debug set to {environment} Running in Development mode")

application = get_wsgi_application()
