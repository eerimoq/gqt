import json
import sys
import argparse
import curses
import requests

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
                if i > -1:
                    field.cursor = False
                    self.fields[i].cursor = True

                    return CursorMove.DONE
                elif i == -1:
                    return CursorMove.FOUND
            else:
                cursor_move = field.key_up()

                if cursor_move == CursorMove.FOUND:
                    # ToDo: Find previous cursor position.
                    cursor_move = CursorMove.DONE

                if cursor_move == CursorMove.DONE:
                    return CursorMove.DONE

        return CursorMove.NOT_FOUND

    def key_down(self):
        for i, field in enumerate(self.fields, 1):
            if field.cursor:
                if i < len(self.fields):
                    field.cursor = False
                    self.fields[i].cursor = True

                    return CursorMove.DONE
            else:
                cursor_move = field.key_down()

                if cursor_move == CursorMove.FOUND:
                    # ToDo: Find next cursor position.
                    cursor_move = CursorMove.DONE

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

        for field in self.fields:
            if isinstance(field, Leaf):
                if field.is_selected:
                    items.append(field.name)
            elif isinstance(field, Object):
                if field.is_expanded:
                    items.append(field.query())

        if items:
            if self.is_root:
                return '{' + ' '.join(items) + '}'
            else:
                return f'{self.name} {{' + ' '.join(items) + '}'
        else:
            return ''


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
        self.value = None
        self.cursor = False

    def show(self, stdscr, y, x, cursor):
        if self.cursor:
            cursor[0] = y
            cursor[1] = x + len(self.name) + 6

        stdscr.addstr(y, x, '-', curses.color_pair(1))
        stdscr.addstr(y, x + 2, f'{self.name}*:')
        stdscr.addstr(y, x + 2 + len(self.name) + 3, '""', curses.color_pair(2))

        return y + 1


def update(stdscr, url, root, key):
    if key == 'KEY_UP':
        root.key_up()
    elif key == 'KEY_DOWN':
        root.key_down()
    elif key == 'KEY_LEFT':
        root.key_left()
    elif key == 'KEY_RIGHT':
        root.key_right()
    elif key == ' ':
        root.select()
    elif key == '\n':
        return False

    stdscr.erase()
    stdscr.addstr(0, 0, url, curses.A_UNDERLINE)
    cursor = [0, 0]
    root.show(stdscr, 1, 0, cursor)
    stdscr.move(*cursor)
    stdscr.refresh()

    return True


def load_tree():
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
                                  Leaf('name')
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

    query = root.query()
    response = requests.post(url, data=f'{{"query":"{query}"}}')

    if response.status_code != 200:
        sys.exit(1)

    response = response.json()

    if 'errors' in response:
        sys.exit(2)

    return json.dumps(response['data'], indent=4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url',
                        nargs='?',
                        default='https://mys-lang.org/graphql',
                        help='GraphQL end-point URL.')
    args = parser.parse_args()

    try:
        print(curses.wrapper(selector, args.url))
    except KeyboardInterrupt:
        sys.exit(1)
