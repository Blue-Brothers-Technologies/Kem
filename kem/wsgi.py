"""Exponer la aplicación Django para servidores compatibles con WSGI."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kem.settings")
application = get_wsgi_application()
