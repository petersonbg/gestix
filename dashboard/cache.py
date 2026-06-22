from django.core.cache import cache


DASHBOARD_CACHE_VERSION_KEY = 'dashboard:dados:versao'


def obter_versao_cache_dashboard():
    return cache.get_or_set(DASHBOARD_CACHE_VERSION_KEY, 1, timeout=None)


def chave_cache_dashboard(chave):
    return f'{chave}:v{obter_versao_cache_dashboard()}'


def invalidar_cache_dashboard(*args, **kwargs):
    try:
        cache.incr(DASHBOARD_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(DASHBOARD_CACHE_VERSION_KEY, 2, timeout=None)