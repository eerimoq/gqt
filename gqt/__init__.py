import argparse
import curses


class Node:

    def show(self, stdscr, y, x, cursor):
        pass

    def key_up(self):
        return False

    def key_down(self):
        return False

    def key_left(self):
        return False

    def key_right(self):
        return False

    def select(self):
        pass

    def query(self):
        pass


class Object(Node):

    def __init__(self, name, fields, is_root=False):
        self.is_expanded = False
        self.name = name
        self.fields = fields
        self.cursor = False
        self.is_root = is_root

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

                    return True
            else:
                if field.key_up():
                    return True

        return False

    def key_down(self):
        for i, field in enumerate(self.fields, 1):
            if field.cursor:
                if i < len(self.fields):
                    field.cursor = False
                    self.fields[i].cursor = True

                    return True
            else:
                if field.key_down():
                    return True

        return False

    def key_right(self):
        for i, field in enumerate(self.fields, 0):
            if field.cursor:
                if isinstance(field, Object):
                    field.cursor = False
                    field.is_expanded = True
                    field.fields[0].cursor = True

                return True
            else:
                if field.key_right():
                    return True

        return False

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
            Object('statistics', [Leaf('number_of_downloads')])
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

    return root.query()

    res = ''
    res += '{\n'
    res += '  "data": {\n'
    res += '    "standard_library": {\n'
    res += '      "package": {\n'
    res += '        "name": "argparse",\n'
    res += '        "latest_release": {\n'
    res += '          "version": "0.1.0"\n'
    res += '        }\n'
    res += '      }\n'
    res += '    }\n'
    res += '  }\n'
    res += '}'

    return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url',
                        nargs='?',
                        default='https://mys-lang.org/graphql',
                        help='GraphQL end-point URL.')
    args = parser.parse_args()

    print(curses.wrapper(selector, args.url))
