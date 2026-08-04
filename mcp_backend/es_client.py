from functools import lru_cache

from elasticsearch import Elasticsearch

from common.settings import settings


@lru_cache(maxsize=1)
def get_es_client():
    return Elasticsearch(settings.es_host)
