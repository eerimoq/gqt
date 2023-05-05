import json
import pickle
import shutil
from base64 import b64decode
from base64 import b64encode

from xdg import XDG_CACHE_HOME

from .experimental import is_experimental
from .tree import load_tree_from_json
from .version import __version__

CACHE_PATH = XDG_CACHE_HOME / 'gqt' / 'cache'


def make_endpoint_cache_name(endpoint):
    return b64encode(endpoint.encode('utf-8')).decode('utf-8')


def make_query_pickle_path(endpoint, query_name):
    name = make_endpoint_cache_name(endpoint)
    endpoint_path = CACHE_PATH / __version__ / name

    if query_name is None:
        return endpoint_path / 'query.pickle'
    else:
        return endpoint_path / 'query_names' / query_name / 'query.pickle'


def make_query_json_path(endpoint, query_name):
    name = make_endpoint_cache_name(endpoint)
    endpoint_path = CACHE_PATH / name

    if query_name is None:
        return endpoint_path / 'query.json'
    else:
        return endpoint_path / 'query_names' / query_name / 'query.json'


def read_tree_from_cache(endpoint, query_name):
    if is_experimental():
        return load_tree_from_json(
            json.loads(make_query_json_path(endpoint, query_name).read_text()))
    else:
        return pickle.loads(make_query_pickle_path(endpoint, query_name).read_bytes())


def write_tree_to_cache(tree, endpoint, query_name):
    if is_experimental():
        path = make_query_json_path(endpoint, query_name)
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(json.dumps(tree.to_json()))
    else:
        path = make_query_pickle_path(endpoint, query_name)
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(pickle.dumps(tree))


def clear_cache():
    shutil.rmtree(CACHE_PATH, ignore_errors=True)


def get_cached_queries():
    cache_path = CACHE_PATH / __version__
    items = []

    for path in cache_path.glob('*'):
        endpoint = b64decode(path.name).decode()

        if (path / 'query.pickle').exists():
            items.append((endpoint, '<default>'))

        for query_name_path in path.glob('query_names/*'):
            query_name = query_name_path.name
            items.append((endpoint, query_name))

    return items
