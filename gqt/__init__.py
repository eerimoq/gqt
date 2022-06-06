import argparse
import curses
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from hashlib import blake2b

import requests
import yaml
from graphql import build_client_schema
from graphql import get_introspection_query
from graphql import print_schema

from .cache import CACHE_PATH
from .cache import read_cached_schema
from .cache import read_tree_from_cache
from .cache import write_cached_schema
from .cache import write_tree_to_cache
from .screen import addstr
from .screen import move
from .tree import Cursor
from .tree import load_tree_from_schema
from .version import __version__


def default_endpoint():
    return os.environ.get('GQT_ENDPOINT', 'https://mys-lang.org/graphql')


def update(stdscr, endpoint, tree, key, y_offset):
    if key == 'KEY_UP':
        tree.key_up()
    elif key == 'KEY_DOWN':
        tree.key_down()
    elif key == 'KEY_LEFT':
        tree.key_left()
    elif key == 'KEY_RIGHT':
        tree.key_right()
    elif key == ' ':
        tree.select()
    elif key == '\n':
        return True, y_offset
    elif key == 'KEY_RESIZE':
        pass
    elif key is not None:
        tree.key(key)

    cursor = Cursor()

    while True:
        stdscr.erase()
        y_max, x_max = stdscr.getmaxyx()
        y = tree.show(stdscr, y_offset, 2, cursor)

        for i in range(1, y):
            addstr(stdscr, i, 0, '│')

        if cursor.y < 1:
            y_offset += 1
        elif cursor.y >= y_max:
            y_offset -= 1
        else:
            addstr(stdscr, 0, 0, ' ' * x_max)
            addstr(stdscr, 0, x_max - len(endpoint), endpoint)
            addstr(stdscr, 0, 0, f'╭─ Query ─ {tree.cursor_type()} ')
            break

    move(stdscr, cursor.y, cursor.x)
    stdscr.refresh()

    return False, y_offset


def fetch_schema(endpoint):
    try:
        return read_cached_schema(endpoint)
    except Exception:
        pass

    schema, checksum = fetch_schema_from_endpoint(endpoint)
    write_cached_schema(schema, checksum, endpoint)

    return schema, checksum


def fetch_schema_from_endpoint(endpoint):
    response = post(endpoint, {"query": get_introspection_query()})
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

    return load_tree_from_schema(schema), checksum


def selector(stdscr, endpoint, tree):
    stdscr.clear()
    stdscr.keypad(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)

    y_offset = 1
    update(stdscr, endpoint, tree, None, y_offset)
    done = False

    while not done:
        try:
            key = stdscr.getkey()
        except curses.error:
            continue

        done, y_offset = update(stdscr, endpoint, tree, key, y_offset)


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
    tree, checksum = load_tree(endpoint)

    with redirect_stdout_to_stderr():
        curses.wrapper(selector, endpoint, tree)

    write_tree_to_cache(tree, endpoint, checksum)

    return tree


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
                query = json.dumps(create_query(query))
                print(CURL_COMMAND.format(endpoint=args.endpoint, query=query))
            else:
                data = execute_query(args.endpoint, create_query(query), args.yaml)

                if args.yaml:
                    show(data, 'yaml')
                else:
                    show(data, 'json')
    except KeyboardInterrupt:
        sys.exit(1)
    #except BaseException as error:
    #    sys.exit(f'error: {error}')
