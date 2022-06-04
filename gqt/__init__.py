import subprocess
import argparse
import curses
import json
import os
import pickle
import shutil
import sys
from base64 import b64encode
from contextlib import contextmanager
from hashlib import blake2b

import requests
import yaml
from graphql import build_client_schema
from graphql import print_schema
from xdg import XDG_CACHE_HOME

from .screen import addstr
from .tree import CursorMove
from .tree import load_tree_from_schema
from .tree import set_cursor_up
from .version import __version__

CACHE_PATH = XDG_CACHE_HOME / 'gqt' / 'cache'

SCHEMA_QUERY = {
    "query": (
        "\n    query IntrospectionQuery {\n      __schema {\n        queryType { "
        "name }\n        mutationType { name }\n        subscriptionType { name }"
        "\n        types {\n          ...FullType\n        }\n        directives "
        "{\n          name\n          description\n          locations\n         "
        " args {\n            ...InputValue\n          }\n        }\n      }\n   "
        " }\n\n    fragment FullType on __Type {\n      kind\n      name\n      d"
        "escription\n      fields(includeDeprecated: true) {\n        name\n     "
        "   description\n        args {\n          ...InputValue\n        }\n    "
        "    type {\n          ...TypeRef\n        }\n        isDeprecated\n     "
        "   deprecationReason\n      }\n      inputFields {\n        ...InputValu"
        "e\n      }\n      interfaces {\n        ...TypeRef\n      }\n      enumV"
        "alues(includeDeprecated: true) {\n        name\n        description\n   "
        "     isDeprecated\n        deprecationReason\n      }\n      possibleTyp"
        "es {\n        ...TypeRef\n      }\n    }\n\n    fragment InputValue on _"
        "_InputValue {\n      name\n      description\n      type { ...TypeRef }\n"
        "      defaultValue\n    }\n\n    fragment TypeRef on __Type {\n      kin"
        "d\n      name\n      ofType {\n        kind\n        name\n        ofTyp"
        "e {\n          kind\n          name\n          ofType {\n            kin"
        "d\n            name\n            ofType {\n              kind\n         "
        "     name\n              ofType {\n                kind\n               "
        " name\n                ofType {\n                  kind\n               "
        "   name\n                  ofType {\n                    kind\n         "
        "           name\n                  }\n                }\n              }"
        "\n            }\n          }\n        }\n      }\n    }\n  ")
}


def default_endpoint():
    return os.environ.get('GQT_ENDPOINT', 'https://mys-lang.org/graphql')


def update(stdscr, endpoint, root, key):
    if key == 'KEY_UP':
        root.key_up()
    elif key == 'KEY_DOWN':
        if root.key_down() == CursorMove.FOUND:
            set_cursor_up(root.fields[-1])
    elif key == 'KEY_LEFT':
        root.key_left()
    elif key == 'KEY_RIGHT':
        root.key_right()
    elif key == ' ':
        root.select()
    elif key == '\n':
        return False
    elif key == 'KEY_RESIZE':
        pass
    elif key is not None:
        root.key(key)

    stdscr.erase()
    _, x_max = stdscr.getmaxyx()
    addstr(stdscr, 0, x_max - len(endpoint), endpoint)
    addstr(stdscr, 0, 0, '╭─ Query')
    cursor = [0, 0]
    y = root.show(stdscr, 1, 2, cursor)

    for i in range(1, y):
        addstr(stdscr, i, 0, '│')

    try:
        stdscr.move(*cursor)
    except curses.error:
        pass

    stdscr.refresh()

    return True


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


def fetch_schema(endpoint):
    try:
        return read_cached_schema(endpoint)
    except Exception:
        pass

    schema, checksum = fetch_schema_from_endpoint(endpoint)
    write_cached_schema(schema, checksum, endpoint)

    return schema, checksum

def fetch_schema_from_endpoint(endpoint):
    response = post(endpoint, SCHEMA_QUERY)
    checksum = blake2b(response.content).hexdigest()
    response = response.json()

    if 'errors' in response:
        sys.exit(response['errors'])

    return response['data'], checksum


def load_tree(endpoint):
    schema, checksum = fetch_schema(endpoint)

    try:
        return read_tree_from_cache(endpoint, checksum), checksum
    except Exception:
        pass

    root = load_tree_from_schema(schema)
    root.fields[0].cursor = True

    return root, checksum


def selector(stdscr, endpoint, root):
    stdscr.clear()
    stdscr.keypad(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)

    update(stdscr, endpoint, root, None)

    while True:
        try:
            key = stdscr.getkey()
        except curses.error:
            continue

        if not update(stdscr, endpoint, root, key):
            break


def create_query(query):
    return {"query": query}


def last_query(endpoint):
    checksum = fetch_schema(endpoint)[1]

    return read_tree_from_cache(endpoint, checksum)


@contextmanager
def redirect_stdout_to_stderr():
    original_stdout = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

    try:
        yield
    finally:
        os.dup2(original_stdout, sys.stdout.fileno())
        os.close(original_stdout)


def query_builder(endpoint):
    root, checksum = load_tree(endpoint)

    with redirect_stdout_to_stderr():
        curses.wrapper(selector, endpoint, root)

    write_tree_to_cache(root, endpoint, checksum)

    return root


def post(endpoint, query):
    response = requests.post(endpoint, json=query)

    if response.status_code != 200:
        print(response.text, file=sys.stderr)
        response.raise_for_status()

    return response


def execute_query(endpoint, query, format_yaml):
    json_response = post(endpoint, query).json()

    if 'errors' in json_response:
        sys.exit(json_response['errors'])

    json_data = json.dumps(json_response['data'], ensure_ascii=False, indent=4)

    if format_yaml:
        return yaml.dump(yaml.load(json_data, Loader=yaml.Loader),
                         allow_unicode=True,
                         sort_keys=False,
                         Dumper=yaml.Dumper).strip()
    else:
        return json_data


CURL_COMMAND = '''\
curl -X POST \\
     -H 'content-type: application/json' \\
     '{endpoint}' \\
     -d '{query}'\
'''


def show(data, language):
    if 'GQT_NO_BAT' not in os.environ and shutil.which('bat'):
        data += '\n'
        subprocess.run(['bat', '-p', '-l', language], input=data, text=True)
    else:
        print(data)


def main():
    parser = argparse.ArgumentParser(
        description='Set GQT_NO_BAT to disable using bat for styling.')
    parser.add_argument('--version',
                        action='version',
                        version=__version__,
                        help='Print version information and exit.')
    parser.add_argument(
        '-e', '--endpoint',
        default=default_endpoint(),
        help=('GraphQL endpoint (default: %(default)s). Set environment variable '
              'GQT_ENDPOINT to override default value.'))
    parser.add_argument('-r', '--repeat',
                        action='store_true',
                        help='Repeat last query.')
    parser.add_argument('-y', '--yaml',
                        action='store_true',
                        help='Print the response as YAML instead of JSON.')
    parser.add_argument('-q', '--query',
                        action='store_true',
                        help='Print the query instead of executing it.')
    parser.add_argument('-c', '--curl',
                        action='store_true',
                        help='Print the cURL command instead of executing it.')
    parser.add_argument('-p', '--print-schema',
                        action='store_true',
                        help='Print the schema.')
    parser.add_argument('-C', '--clear-cache',
                        action='store_true',
                        help='Clear the cache and exit.')
    args = parser.parse_args()

    CACHE_PATH.mkdir(exist_ok=True, parents=True)

    if args.clear_cache:
        shutil.rmtree(CACHE_PATH)
        return

    try:
        if args.print_schema:
            schema, _ = fetch_schema_from_endpoint(args.endpoint)
            schema = print_schema(build_client_schema(schema))
            show(schema, 'graphql')
        else:
            if args.repeat:
                query = last_query(args.endpoint)
            else:
                query = query_builder(args.endpoint)

            query = query.query()

            if args.query:
                show(str(query), 'graphql')
            elif args.curl:
                print(CURL_COMMAND.format(endpoint=args.endpoint,
                                          query=json.dumps(create_query(query))))
            else:
                data = execute_query(args.endpoint, create_query(query), args.yaml)

                if args.yaml:
                    show(data, 'yaml')
                else:
                    show(data, 'json')
    except KeyboardInterrupt:
        sys.exit(1)
    except BaseException as error:
        sys.exit(f'error: {error}')
