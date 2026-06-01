"""ASGI config for the GESTIX project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestix.settings')

application = get_asgi_application()
