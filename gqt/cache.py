import pickle
from base64 import b64encode

from xdg import XDG_CACHE_HOME

from .version import __version__

CACHE_PATH = XDG_CACHE_HOME / 'gqt' / 'cache'


def make_endpoint_cache_name(endpoint):
    return b64encode(endpoint.encode('utf-8')).decode('utf-8')


def make_query_pickle_path(endpoint, checksum):
    name = make_endpoint_cache_name(endpoint)

    return CACHE_PATH / __version__ / name / f'query-{checksum}.pickle'


def read_tree_from_cache(endpoint, checksum):
    return pickle.loads(make_query_pickle_path(endpoint, checksum).read_bytes())


def write_tree_to_cache(root, endpoint, checksum):
    path = make_query_pickle_path(endpoint, checksum)
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(pickle.dumps(root))


def make_schema_pickle_path(endpoint):
    name = make_endpoint_cache_name(endpoint)

    return CACHE_PATH / __version__ / name / 'schema.pickle'


def read_cached_schema(endpoint):
    return pickle.loads(make_schema_pickle_path(endpoint).read_bytes())


def write_cached_schema(schema, checksum, endpoint):
    path = make_schema_pickle_path(endpoint)
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(pickle.dumps((schema, checksum)))
