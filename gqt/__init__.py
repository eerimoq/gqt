import argparse
import curses


class Node:

    def show(self, stdscr, y, x, cursor):
        pass


class Object(Node):

    def __init__(self, name, fields):
        self.is_expanded = False
        self.name = name
        self.fields = fields
        self.cursor = False

    def show(self, stdscr, y, x, cursor):
        if self.cursor:
            cursor[0] = y
            cursor[1] = x

        if not self.is_expanded:
            stdscr.addstr(y, x, '>', curses.color_pair(1))
            stdscr.addstr(y, x + 2, self.name)
            y += 1
        else:
            stdscr.addstr(y, x, '', curses.color_pair(1))
            stdscr.addstr(y, x + 2, self.name)
            y += 1

            for field in self.fields:
                y = field.show(stdscr, y, x + 2, cursor)

        return y


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


class Argument(Node):

    def __init__(self, name):
        self.name = name
        self.value = None
        self.cursor = False

    def show(self, stdscr, y, x, cursor):
        if self.cursor:
            cursor[0] = y
            cursor[1] = x

        stdscr.addstr(y, x, '■', curses.color_pair(1))
        stdscr.addstr(y, x + 2, f'{self.name}*:')
        stdscr.addstr(y, x + 2 + len(self.name) + 3, '""', curses.color_pair(2))

        return y + 1


def key_up(fields):
    pass


def key_down(fields):
    pass


def key_left(fields):
    pass


def key_right(fields):
    pass


def select(fields):
    pass


def update(stdscr, fields, key):
    if key == 'KEY_UP':
        key_up(fields)
    elif key == 'KEY_DOWN':
        key_down(fields)
    elif key == 'KEY_LEFT':
        key_left(fields)
    elif key == 'KEY_RIGHT':
        key_right(fields)
    elif key == ' ':
        select(fields)
    elif key == '\n':
        return False

    stdscr.erase()
    y = 0
    cursor = [0, 0]

    for field in fields:
        y = field.show(stdscr, y, 0, cursor)

    stdscr.move(*cursor)
    stdscr.refresh()

    return True


def load_tree():
    fields = [
        Object('activities', []),
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
                   Object('packages', [])
               ]),
        Object('statistics', [Leaf('foo')])
    ]
    fields[0].cursor = True

    return fields


def selector(stdscr):
    stdscr.clear()
    stdscr.keypad(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

    fields = load_tree()
    update(stdscr, fields, None)

    # Down.
    fields[0].cursor = False
    fields[1].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Right.
    fields[0].cursor = False
    fields[1].is_expanded = True
    fields[1].fields[0].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[0].cursor = False
    fields[1].fields[1].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[1].cursor = False
    fields[1].fields[2].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Right.
    fields[1].fields[2].cursor = False
    fields[1].fields[2].is_expanded = True
    fields[1].fields[2].fields[0].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[2].fields[0].cursor = False
    fields[1].fields[2].fields[1].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[2].fields[1].cursor = False
    fields[1].fields[2].fields[2].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[2].fields[2].cursor = False
    fields[1].fields[2].fields[3].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[2].fields[3].cursor = False
    fields[1].fields[2].fields[4].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Space.
    fields[1].fields[2].fields[4].is_selected = True
    update(stdscr, fields, stdscr.getkey())

    # Up.
    fields[1].fields[2].fields[4].cursor = False
    fields[1].fields[2].fields[3].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Right.
    fields[1].fields[2].fields[3].cursor = False
    fields[1].fields[2].fields[3].is_expanded = True
    fields[1].fields[2].fields[3].fields[0].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Down.
    fields[1].fields[2].fields[3].fields[0].cursor = False
    fields[1].fields[2].fields[3].fields[1].cursor = True
    update(stdscr, fields, stdscr.getkey())

    # Space.
    fields[1].fields[2].fields[3].fields[1].is_selected = True
    update(stdscr, fields, stdscr.getkey())

    stdscr.getkey()

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
    parser.add_argument('url')
    args = parser.parse_args()
    
    print(curses.wrapper(selector))
