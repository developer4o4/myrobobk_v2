from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Local da oddiy DB cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Throttle ni local da o'chiramiz
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # type: ignore[name-defined]
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# INSTALLED_APPS += ["django_extensions"]  # type: ignore[name-defined]
