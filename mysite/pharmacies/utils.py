from elasticsearch.helpers import bulk
from django_elasticsearch_dsl.registries import connections
from .documents import ProductDocument
from elasticsearch import Elasticsearch

def bulk_index_products(product_instances):
    es = Elasticsearch(hosts=["http://elasticsearch-node-2:9200", "http://elasticsearch-node-1:9200"])  # Подключение к Elasticsearch
    actions = [
        ProductDocument().get_index_action(product)
        for product in product_instances
    ]
    bulk(client=es, actions=actions)
