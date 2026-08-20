from django.conf import settings
from django.core.cache import cache

CATALOG_VERSION_KEY = "catalog:version"


def catalog_cache_ttl():
    return int(getattr(settings, "CATALOG_CACHE_TTL_SECONDS", 60))


def catalog_version():
    version = cache.get(CATALOG_VERSION_KEY)
    if version is None:
        cache.set(CATALOG_VERSION_KEY, 1, timeout=None)
        return 1
    return int(version)


def invalidate_catalog_cache():
    try:
        cache.incr(CATALOG_VERSION_KEY)
    except ValueError:
        cache.set(CATALOG_VERSION_KEY, 1, timeout=None)


def catalog_cache_get(key):
    return cache.get(key)


def catalog_cache_set(key, value):
    cache.set(key, value, catalog_cache_ttl())
