import json
import shutil
from urllib.parse import quote_plus
from urllib.parse import unquote_plus

from xdg import XDG_DATA_HOME

from .tree import load_tree_from_json

DATABASE_PATH = XDG_DATA_HOME / 'gqt' / 'database'


def make_endpoint_path(endpoint):
    return DATABASE_PATH / quote_plus(endpoint)


def make_query_json_path(endpoint, query_name):
    endpoint_path = make_endpoint_path(endpoint)

    if query_name is not None:
        endpoint_path = endpoint_path / 'query_names' / query_name

    return endpoint_path / 'query.json'


def make_most_recent_query_name_path(endpoint):
    return make_endpoint_path(endpoint) / 'most_recent_query_name.txt'


def read_tree_from_database(endpoint, query_name):
    path = make_query_json_path(endpoint, query_name)

    if not path.exists():
        most_recent_path = make_most_recent_query_name_path(endpoint)

        if most_recent_path.exists():
            query_name = most_recent_path.read_text()
        else:
            query_name = None

        path = make_query_json_path(endpoint, query_name)

    return load_tree_from_json(json.loads(path.read_text()))


def write_tree_to_database(tree, endpoint, query_name):
    path = make_query_json_path(endpoint, query_name)
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(tree.to_json()))
    path = make_most_recent_query_name_path(endpoint)

    if query_name is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    else:
        path.write_text(query_name)


def clear_database():
    shutil.rmtree(DATABASE_PATH, ignore_errors=True)


def get_queries():
    items = []

    for path in DATABASE_PATH.glob('*'):
        endpoint = unquote_plus(path.name)

        if (path / 'query.json').exists():
            items.append((endpoint, '<default>'))

        for query_name_path in path.glob('query_names/*'):
            query_name = query_name_path.name
            items.append((endpoint, query_name))

    return items
