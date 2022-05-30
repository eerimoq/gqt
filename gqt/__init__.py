import os
import pickle
import json
import sys
import argparse
import curses
from contextlib import contextmanager
import requests
from xdg import XDG_CACHE_HOME


CACHE_PICKLE = XDG_CACHE_HOME / 'gqt' / 'query.pickle'


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
            stdscr.addstr(y, x, '', curses.color_pair(1))
            stdscr.addstr(y, x + 2, self.name)
            y += 1

            for field in self.fields:
                y = field.show(stdscr, y, x + 2, cursor)
        else:
            stdscr.addstr(y, x, '>', curses.color_pair(1))
            stdscr.addstr(y, x + 2, self.name)
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
                arguments.append(f'{field.name}:"{field.value}"')
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
            stdscr.addstr(y, x, '■', curses.color_pair(1))
        else:
            stdscr.addstr(y, x, '□', curses.color_pair(1))

        stdscr.addstr(y, x + 2, self.name)

        return y + 1

    def select(self):
        if self.cursor:
            self.is_selected = not self.is_selected


class Argument(Node):

    def __init__(self, name):
        self.name = name
        self.value = ''
        self.cursor = False

    def show(self, stdscr, y, x, cursor):
        value = f'"{self.value}"'

        if self.cursor:
            cursor[0] = y
            cursor[1] = x + len(self.name) + 4 + len(value)

        stdscr.addstr(y, x, '-', curses.color_pair(1))
        stdscr.addstr(y, x + 2, f'{self.name}*:')
        stdscr.addstr(y, x + 2 + len(self.name) + 3, value, curses.color_pair(2))

        return y + 1

    def key(self, key):
        if key in ['KEY_BACKSPACE', '\b', 'KEY_DC', '\x7f']:
            self.value = self.value[:-1]
        else:
            self.value += key


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
    stdscr.addstr(0, 0, url, curses.A_UNDERLINE)
    cursor = [0, 0]
    root.show(stdscr, 1, 0, cursor)
    stdscr.move(*cursor)
    stdscr.refresh()

    return True


def read_tree_from_cache():
    return pickle.loads(CACHE_PICKLE.read_bytes())


def write_tree_to_cache(root):
    CACHE_PICKLE.parent.mkdir(exist_ok=True)
    CACHE_PICKLE.write_bytes(pickle.dumps(root))


def load_tree():
    try:
        return read_tree_from_cache()
    except Exception:
        pass

    root = Object(
        None,
        [
            Object('activities',
                   [
                       Leaf('date'),
                       Leaf('kind'),
                       Leaf('message')
                   ]),
            Object('standard_library',
                   [
                       Leaf('number_of_downloads'),
                       Leaf('number_of_packages'),
                       Object('package',
                              [
                                  Argument('name'),
                                  Leaf('builds'),
                                  Leaf('coverage'),
                                  Object('latest_release',
                                         [
                                             Leaf('description'),
                                             Leaf('version')
                                         ]),
                                  Leaf('name'),
                                  Leaf('number_of_downloads')
                              ]),
                       Object('packages',
                              [
                                  Leaf('builds'),
                                  Leaf('coverage'),
                                  Object('latest_release',
                                         [
                                             Leaf('description'),
                                             Leaf('version')
                                         ]),
                                  Leaf('name'),
                                  Leaf('number_of_downloads')
                              ])
                   ]),
            Object('statistics',
                   [
                       Leaf('start_date_time'),
                       Leaf('total_number_of_requests'),
                       Leaf('number_of_unique_visitors'),
                       Leaf('number_of_graphql_requests'),
                       Leaf('no_idle_client_handlers')
                   ])
        ],
        True)
    root.fields[0].cursor = True

    return root


def selector(stdscr, url):
    stdscr.clear()
    stdscr.keypad(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)

    root = load_tree()
    update(stdscr, url, root, None)

    while True:
        if not update(stdscr, url, root, stdscr.getkey()):
            break

    write_tree_to_cache(root)

    return create_query(root)


def create_query(root):
    query = root.query().replace('"', '\\"')

    return f'{{"query":"{query}"}}'


def last_query():
    return create_query(read_tree_from_cache())


def execute_query(url, query):
    response = requests.post(url, data=query)

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
        query = last_query()
    else:
        try:
            with redirect_stdout_to_stderr():
                query = curses.wrapper(selector, args.url)
        except KeyboardInterrupt:
            sys.exit(1)

    if args.query:
        print(query)
    else:
        print(execute_query(args.url, query))
