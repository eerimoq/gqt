import pickle
from base64 import b64encode

from xdg import XDG_CACHE_HOME

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


def read_tree_from_cache(endpoint, query_name):
    return pickle.loads(make_query_pickle_path(endpoint, query_name).read_bytes())


def write_tree_to_cache(root, endpoint, query_name):
    path = make_query_pickle_path(endpoint, query_name)
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(pickle.dumps(root))
