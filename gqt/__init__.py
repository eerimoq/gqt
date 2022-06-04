import yaml
import shutil
from base64 import b64encode
from hashlib import blake2b
import os
import pickle
import json
import sys
import argparse
import curses
from contextlib import contextmanager
import requests
from xdg import XDG_CACHE_HOME
from readlike import edit
from graphql import print_schema
from graphql import build_client_schema
from .version import __version__


KEY_BINDINGS = {
    'KEY_BACKSPACE': 'backspace',
    '\b': 'backspace',
    'KEY_DC': 'backspace',
    '\x7f': 'backspace',
    '\x01': 'ctrl a',
    # '': 'ctrl b',
    '\x04': 'ctrl d',
    '\x05': 'ctrl e',
    # '': 'ctrl f',
    # '': 'ctrl h',
    '\x0b': 'ctrl k',
    # '': 'ctrl meta h',
    '\x14': 'ctrl t',
    # '': 'ctrl u',
    # '': 'ctrl w',
    # '': 'delete',
    # '': 'end',
    # '': 'home',
    'KEY_LEFT': 'left',
    # '': 'meta \\',
    # '': 'meta b',
    '\x1b\x7f': 'meta backspace',
    # '': 'meta c',
    '\x1bd': 'meta d',
    # '': 'meta delete',
    # '': 'meta f',
    # '': 'meta l',
    '\x1bb': 'meta left',
    '\x1bf': 'meta right',
    # '': 'meta t',
    # '': 'meta u',
    'KEY_RIGHT': 'right'
}

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


class CursorMove:
    DONE = 0
    FOUND = 1
    NOT_FOUND = 2


class Node:

    def show(self, stdscr, y, x, cursor):
        pass

    def key_up(self):
        return CursorMove.NOT_FOUND

    def key_down(self):
        return CursorMove.NOT_FOUND

    def key_left(self):
        return CursorMove.NOT_FOUND

    def key_right(self):
        return CursorMove.NOT_FOUND

    def select(self):
        pass

    def key(self, key):
        pass

    def query(self):
        pass


class Object(Node):

    def __init__(self, name, fields, is_root=False):
        self.name = name
        self.fields = fields
        self.cursor = False
        self.is_root = is_root
        self.is_expanded = is_root

    def show(self, stdscr, y, x, cursor):
        if self.cursor:
            cursor[0] = y
            cursor[1] = x

        if self.is_root:
            for field in self.fields:
                y = field.show(stdscr, y, x, cursor)
        elif self.is_expanded:
            addstr(stdscr, y, x, '▼', curses.color_pair(1))
            addstr(stdscr, y, x + 2, self.name)
            y += 1

            for field in self.fields:
                y = field.show(stdscr, y, x + 2, cursor)
        else:
            addstr(stdscr, y, x, '▶', curses.color_pair(1))
            addstr(stdscr, y, x + 2, self.name)
            y += 1

        return y

    def key_up(self):
        if not self.is_expanded:
            return CursorMove.NOT_FOUND

        for i, field in enumerate(self.fields, -1):
            if field.cursor:
                if i > -1:
                    field.cursor = False
                    set_cursor_up(self.fields[i])
                elif not self.is_root:
                    field.cursor = False
                    self.cursor = True

                return CursorMove.DONE
            else:
                cursor_move = field.key_up()

                if cursor_move == CursorMove.FOUND:
                    if i == -1:
                        return CursorMove.FOUND
                    else:
                        cursor_move = set_cursor_up(self.fields[i])

                    if cursor_move == CursorMove.FOUND:
                        return CursorMove.FOUND

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def key_down(self):
        if not self.is_expanded:
            return CursorMove.NOT_FOUND

        for i, field in enumerate(self.fields, 1):
            if field.cursor:
                if isinstance(field, Object):
                    if field.is_expanded:
                        field.cursor = False
                        field.fields[0].cursor = True

                        return CursorMove.DONE

                field.cursor = False

                if i < len(self.fields):
                    set_cursor_down(self.fields[i])

                    return CursorMove.DONE
                else:
                    return CursorMove.FOUND
            else:
                cursor_move = field.key_down()

                if cursor_move == CursorMove.FOUND:
                    if i < len(self.fields):
                        cursor_move = set_cursor_down(self.fields[i])

                        if cursor_move == CursorMove.FOUND:
                            return CursorMove.FOUND
                    else:
                        return CursorMove.FOUND

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def key_left(self):
        if not self.is_expanded:
            return CursorMove.NOT_FOUND

        for field in self.fields:
            if field.cursor:
                if isinstance(field, Object):
                    if field.is_expanded:
                        field.is_expanded = False
                    elif not self.is_root:
                        field.cursor = False
                        self.cursor = True

                    return CursorMove.DONE
                elif isinstance(field, Argument):
                    if field.tree.cursor_at_input_field:
                        field.key_left()

                        return CursorMove.DONE

                field.cursor = False
                self.cursor = True

                return CursorMove.DONE
            else:
                cursor_move = field.key_left()

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def key_right(self):
        if not self.is_expanded:
            return CursorMove.NOT_FOUND

        for field in self.fields:
            if field.cursor:
                if isinstance(field, Object):
                    if field.is_expanded:
                        field.cursor = False
                        field.fields[0].cursor = True
                    else:
                        field.is_expanded = True
                elif isinstance(field, Argument):
                    if field.tree.cursor_at_input_field:
                        field.key_right()

                return CursorMove.DONE
            else:
                cursor_move = field.key_right()

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def select(self):
        if not self.is_expanded:
            return CursorMove.NOT_FOUND

        for field in self.fields:
            field.select()

    def query(self):
        if not self.is_expanded:
            return

        items = []
        arguments = []

        for field in self.fields:
            if isinstance(field, Leaf):
                if field.is_selected:
                    items.append(field.name)
            elif isinstance(field, Argument):
                value = field.query()

                if value is not None:
                    arguments.append(f'{field.name}:{value}')
            elif isinstance(field, Object):
                if field.is_expanded:
                    items.append(field.query())

        if arguments:
            arguments = '(' + ','.join(arguments) + ')'
        else:
            arguments = ''

        if items:
            if self.is_root:
                return '{' + ' '.join(items) + '}'
            else:
                return f'{self.name}{arguments} {{' + ' '.join(items) + '}'
        elif self.is_root:
            sys.exit(f"No fields selected.")
        else:
            sys.exit(f"No fields selected in '{self.name}'.")

    def key(self, key):
        if not self.is_expanded:
            return CursorMove.NOT_FOUND

        for field in self.fields:
            field.key(key)


class Leaf(Node):

    def __init__(self, name):
        self.is_selected = False
        self.name = name
        self.cursor = False

    def show(self, stdscr, y, x, cursor):
        if self.cursor:
            cursor[0] = y
            cursor[1] = x

        if self.is_selected:
            addstr(stdscr, y, x, '■', curses.color_pair(1))
        else:
            addstr(stdscr, y, x, '□', curses.color_pair(1))

        addstr(stdscr, y, x + 2, self.name)

        return y + 1

    def select(self):
        if self.cursor:
            self.is_selected = not self.is_selected


class Argument(Node):

    def __init__(self, name, type, tree):
        self.name = name
        self.type = type
        self.tree = tree
        self.value = ''
        self.pos = 0
        self.cursor = False
        self.symbol = '■'
        self.meta = False

    def is_string(self):
        item = self.type

        while item['kind'] == 'NON_NULL':
            item = item['ofType']

        return item['name'] in ['String', 'ID']

    def show(self, stdscr, y, x, cursor):
        if self.is_string():
            value = f'"{self.value}"'
            offset = 1
        else:
            value = str(self.value)
            offset = 0

        if self.cursor:
            cursor[0] = y

            if self.tree.cursor_at_input_field:
                cursor[1] = x + len(self.name) + 4 + self.pos + offset
            else:
                cursor[1] = x

        addstr(stdscr, y, x, self.symbol, curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        addstr(stdscr, y, x + 2 + len(self.name) + 2, value, curses.color_pair(2))

        return y + 1

    def next_symbol(self):
        if self.symbol == '■':
            self.symbol = '□'
        elif self.symbol == '$':
            self.symbol = '■'
        else:
            self.symbol = '$'

    def key_left(self):
        self.key('KEY_LEFT')

    def key_right(self):
        self.key('KEY_RIGHT')

    def key(self, key):
        if not self.cursor:
            return

        if key == '\t':
            self.tree.cursor_at_input_field = not self.tree.cursor_at_input_field
        elif self.tree.cursor_at_input_field:
            if self.meta:
                key = '\x1b' + key
                self.meta = False
            elif key == '\x1b':
                self.meta = True

                return

            self.value, self.pos = edit(self.value,
                                        self.pos,
                                        KEY_BINDINGS.get(key, key))

    def select(self):
        if not self.cursor:
            return

        if self.tree.cursor_at_input_field:
            self.key(' ')
        else:
            self.next_symbol()

    def query(self):
        if not self.value:
            return None

        if self.is_string():
            return f'"{self.value}"'
        else:
            return str(self.value)


class Tree:

    def __init__(self):
        self.cursor_at_input_field = False


def set_cursor_up(field):
    if isinstance(field, Object):
        if not field.is_expanded:
            field.cursor = True

            return CursorMove.DONE
        else:
            return set_cursor_up(field.fields[-1])
    else:
        field.cursor = True

        return CursorMove.DONE


def set_cursor_down(field):
    if isinstance(field, Object):
        field.cursor = True

        return CursorMove.DONE
    else:
        field.cursor = True

        return CursorMove.DONE


def update(stdscr, endpoint, root, key):
    if key == 'KEY_UP':
        if root.key_up() == CursorMove.FOUND:
            set_cursor_down(root.fields[0])
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
    y_max, x_max = stdscr.getmaxyx()
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


def addstr(stdscr, y, x, text, attrs=0):
    try:
        stdscr.addstr(y, x, text, attrs)
    except curses.error:
        pass


def make_endpoint_cache_name(endpoint):
    return b64encode(endpoint.encode('utf-8')).decode('utf-8')


def make_cache_name(checksum):
    return f'{__version__}-{checksum}'


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


def find_type(types, name):
    for type in types:
        if type['name'] == name:
            return type

    raise Exception(f"Type '{name}' not found in schema.")


def build_field(types, field, tree):
    try:
        name = field['name']
    except Exception:
        sys.exit("No field name.")

    item = field['type']

    while item['kind'] in ['NON_NULL', 'LIST']:
        item = item['ofType']

    if item['kind'] == 'OBJECT':
        return Object(name,
                      ObjectFields(field['args'],
                                   find_type(types, item['name'])['fields'],
                                   types,
                                   tree))
    else:
        return Leaf(name)


class ObjectFieldsIterator:

    def __init__(self, fields):
        self._fields = fields
        self._index = 0

    def __next__(self):
        if self._index < len(self._fields):
            self._index += 1

            return self._fields[self._index - 1]
        else:
            raise StopIteration()


class ObjectFields:

    def __init__(self, arguments, fields, types, tree):
        self._arguments_info = arguments
        self._fields_info = fields
        self._types = types
        self._tree = tree
        self._fields = None

    def fields(self):
        if self._fields is None:
            self._fields = [
                Argument(arg['name'], arg['type'], self._tree)
                for arg in self._arguments_info
            ] + [
                build_field(self._types, field, self._tree)
                for field in self._fields_info
            ]

        return self._fields

    def __iter__(self):
        return ObjectFieldsIterator(self.fields())

    def __len__(self):
        return len(self.fields())

    def __getitem__(self, key):
        return self.fields()[key]


def load_tree_from_schema(schema):
    types = schema['__schema']['types']
    query = find_type(types, schema['__schema']['queryType']['name'])
    tree = Tree()

    return Object(None,
                  ObjectFields([], query['fields'], types, tree),
                  True)


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


def main():
    parser = argparse.ArgumentParser()
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
            print(print_schema(build_client_schema(schema)))
        else:
            if args.repeat:
                query = last_query(args.endpoint)
            else:
                query = query_builder(args.endpoint)

            query = query.query()

            if args.query:
                print(query)
            elif args.curl:
                print(CURL_COMMAND.format(endpoint=args.endpoint,
                                          query=json.dumps(create_query(query))))
            else:
                print(execute_query(args.endpoint, create_query(query), args.yaml))
    except KeyboardInterrupt:
        sys.exit(1)
    except BaseException as error:
        sys.exit(f'error: {error}')
