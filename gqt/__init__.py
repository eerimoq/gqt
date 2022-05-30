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
            addstr(stdscr, y, x, '', curses.color_pair(1))
            addstr(stdscr, y, x + 2, self.name)
            y += 1

            for field in self.fields:
                y = field.show(stdscr, y, x + 2, cursor)
        else:
            addstr(stdscr, y, x, '>', curses.color_pair(1))
            addstr(stdscr, y, x + 2, self.name)
            y += 1

        return y

    def key_up(self):
        for i, field in enumerate(self.fields, -1):
            if field.cursor:
                field.cursor = False

                if i > -1:
                    set_cursor_up(self.fields[i])

                    return CursorMove.DONE
                else:
                    return CursorMove.FOUND
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
        for i, field in enumerate(self.fields, 1):
            if field.cursor:
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
            if field.cursor and not self.is_root:
                field.cursor = False
                self.is_expanded = False
                self.cursor = True

                return CursorMove.DONE
            else:
                cursor_move = field.key_left()

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def key_right(self):
        for field in self.fields:
            if field.cursor:
                if isinstance(field, Object):
                    field.cursor = False
                    field.is_expanded = True
                    field.fields[0].cursor = True

                return CursorMove.DONE
            else:
                cursor_move = field.key_right()

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def select(self):
        for field in self.fields:
            field.select()

    def query(self):
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
        else:
            return ''

    def key(self, key):
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

    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.value = ''
        self.cursor = False

    def is_string(self):
        item = self.type

        while item['kind'] == 'NON_NULL':
            item = item['ofType']

        return item['name'] == 'String'

    def show(self, stdscr, y, x, cursor):
        if self.is_string():
            value = f'"{self.value}"'
            offset = 1
        else:
            value = str(self.value)
            offset = 2

        if self.cursor:
            cursor[0] = y
            cursor[1] = x + len(self.name) + 3 + len(value) + offset

        addstr(stdscr, y, x, '-', curses.color_pair(1))
        addstr(stdscr, y, x + 2, f'{self.name}*:')
        addstr(stdscr, y, x + 2 + len(self.name) + 3, value, curses.color_pair(2))

        return y + 1

    def key(self, key):
        if not self.cursor:
            return

        if key in ['KEY_BACKSPACE', '\b', 'KEY_DC', '\x7f']:
            self.value = self.value[:-1]
        else:
            self.value += key

    def query(self):
        if not self.value:
            return None

        if self.is_string():
            return f'"{self.value}"'
        else:
            return str(self.value)


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
        if not field.is_expanded:
            field.cursor = True

            return CursorMove.DONE
        else:
            return set_cursor_down(field.fields[0])
    else:
        field.cursor = True

        return CursorMove.DONE


def update(stdscr, url, root, key):
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
    elif key is not None:
        root.key(key)

    stdscr.erase()
    addstr(stdscr, 0, 0, url, curses.A_UNDERLINE)
    cursor = [0, 0]
    root.show(stdscr, 1, 0, cursor)
    stdscr.move(*cursor)
    stdscr.refresh()

    return True


def addstr(stdscr, y, x, text, attrs=0):
    try:
        stdscr.addstr(y, x, text, attrs)
    except curses.error:
        pass


def read_tree_from_cache(checksum):
    return pickle.loads(CACHE_PATH.joinpath(checksum).read_bytes())


def write_tree_to_cache(root, checksum):
    CACHE_PATH.mkdir(exist_ok=True, parents=True)
    CACHE_PATH.joinpath(checksum).write_bytes(pickle.dumps(root))


def fetch_schema(url):
    response = requests.post(url, json=SCHEMA_QUERY)

    if response.status_code != 200:
        sys.exit(1)

    checksum = blake2b(response.content).hexdigest()
    response = response.json()

    if 'errors' in response:
        sys.exit(response['errors'])

    return response['data'], checksum


def find_type(types, name):
    for type in types:
        if type['name'] == name:
            return type


def build_field(types, field):
    try:
        name = field['name']
    except:
        sys.exit("No field name.")

    item = field['type']

    while item['kind'] in ['NON_NULL', 'LIST']:
        item = item['ofType']

    if item['kind'] == 'OBJECT':
        return Object(name,
                      [
                          Argument(arg['name'], arg['type'])
                          for arg in field['args']
                      ] + [
                          build_field(types, field)
                          for field in find_type(types, item['name'])['fields']
                      ])
    else:
        return Leaf(name)


def load_tree_from_schema(schema):
    types = schema['__schema']['types']
    query = find_type(types, 'Query')

    return Object(None,
                  [
                      build_field(types, field)
                      for field in query['fields']
                  ],
                  True)


def load_tree(url):
    schema, checksum = fetch_schema(url)

    try:
        return read_tree_from_cache(checksum), checksum
    except Exception:
        pass

    root = load_tree_from_schema(schema)
    root.fields[0].cursor = True

    return root, checksum


def selector(stdscr, url):
    stdscr.clear()
    stdscr.keypad(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)

    root, checksum = load_tree(url)
    update(stdscr, url, root, None)

    while True:
        if not update(stdscr, url, root, stdscr.getkey()):
            break

    write_tree_to_cache(root, checksum)

    return create_query(root)


def create_query(root):
    query = root.query()

    return {"query": query}


def last_query(url):
    checksum = fetch_schema(url)[1]

    return create_query(read_tree_from_cache(checksum))


def execute_query(url, query):
    response = requests.post(url, json=query)

    if response.status_code != 200:
        sys.exit(1)

    response = response.json()

    if 'errors' in response:
        sys.exit(response['errors'])

    return json.dumps(response['data'], indent=4)


@contextmanager
def redirect_stdout_to_stderr():
    original_stdout = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

    try:
        yield
    finally:
        os.dup2(original_stdout, sys.stdout.fileno())
        os.close(original_stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url',
                        nargs='?',
                        default='https://mys-lang.org/graphql',
                        help='GraphQL end-point URL.')
    parser.add_argument('-q', '--query',
                        action='store_true',
                        help='Print the query instead of executing it.')
    parser.add_argument('-r', '--repeat',
                        action='store_true',
                        help='Repeat last query.')
    args = parser.parse_args()

    if args.repeat:
        query = last_query(args.url)
    else:
        try:
            with redirect_stdout_to_stderr():
                query = curses.wrapper(selector, args.url)
        except KeyboardInterrupt:
            sys.exit(1)

    if args.query:
        print(json.dumps(query))
    else:
        print(execute_query(args.url, query))
