import json
import shutil
from urllib.parse import quote_plus
from urllib.parse import unquote_plus

from xdg import XDG_CACHE_HOME

from .tree import load_tree_from_json

CACHE_PATH = XDG_CACHE_HOME / 'gqt' / 'cache'


def make_endpoint_cache_name(endpoint):
    return quote_plus(endpoint)


def make_query_json_path(endpoint, query_name):
    name = make_endpoint_cache_name(endpoint)
    endpoint_path = CACHE_PATH / name

    if query_name is not None:
        endpoint_path = endpoint_path / 'query_names' / query_name

    return endpoint_path / 'query.json'


def read_tree_from_cache(endpoint, query_name):
    return load_tree_from_json(
        json.loads(make_query_json_path(endpoint, query_name).read_text()))


def write_tree_to_cache(tree, endpoint, query_name):
    path = make_query_json_path(endpoint, query_name)
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(tree.to_json()))


def clear_cache():
    shutil.rmtree(CACHE_PATH, ignore_errors=True)


def get_cached_queries():
    items = []

    for path in CACHE_PATH.glob('*'):
        endpoint = unquote_plus(path.name)

        if (path / 'query.json').exists():
            items.append((endpoint, '<default>'))

        for query_name_path in path.glob('query_names/*'):
            query_name = query_name_path.name
            items.append((endpoint, query_name))

    return items
