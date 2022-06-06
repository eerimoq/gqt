import pickle
from base64 import b64encode

from xdg import XDG_CACHE_HOME

from .version import __version__

CACHE_PATH = XDG_CACHE_HOME / 'gqt' / 'cache'


def make_endpoint_cache_name(endpoint):
    return b64encode(endpoint.encode('utf-8')).decode('utf-8')


def make_query_pickle_path(endpoint):
    name = make_endpoint_cache_name(endpoint)

    return CACHE_PATH / __version__ / name / 'query.pickle'


def read_tree_from_cache(endpoint):
    return pickle.loads(make_query_pickle_path(endpoint).read_bytes())


def write_tree_to_cache(root, endpoint):
    path = make_query_pickle_path(endpoint)
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(pickle.dumps(root))
