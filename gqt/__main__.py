import curses

class Node:

    def show(self, stdscr, y, x):
        pass

    def has_cursor(self):
        pass


class Object(Node):

    def __init__(self, name, fields):
        self.is_expanded = False
        self.name = name
        self.fields = fields
        self.cursor = False

    def show(self, stdscr, y, x):
        if not self.is_expanded:
            stdscr.addstr(y, x, '>', curses.color_pair(1))
            stdscr.addstr(y, x + 2, self.name)
            y += 1
        else:
            stdscr.addstr(y, x, '', curses.color_pair(1))
            stdscr.addstr(y, x + 2, self.name)
            y += 1

            for field in self.fields:
                y = field.show(stdscr, y, x + 2)

        return y

    def has_cursor(self):
        return self.cursor


class Leaf(Node):

    def __init__(self, name):
        self.is_selected = False
        self.name = name
        self.cursor = False

    def show(self, stdscr, y, x):
        if self.is_selected:
            stdscr.addstr(y, x, '■', curses.color_pair(1))
        else:
            stdscr.addstr(y, x, '□', curses.color_pair(1))

        stdscr.addstr(y, x + 2, self.name)

        return y + 1

    def has_cursor(self):
        return self.cursor


class Argument(Node):

    def __init__(self, name):
        self.name = name
        self.value = None
        self.cursor = False

    def show(self, stdscr, y, x):
        stdscr.addstr(y, x, '■', curses.color_pair(1))
        stdscr.addstr(y, x + 2, f'{self.name}*:')
        stdscr.addstr(y, x + 2 + len(self.name) + 3, '""', curses.color_pair(2))

        return y + 1

    def has_cursor(self):
        return self.cursor


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

    for field in fields:
        y = field.show(stdscr, y, 0)

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


def main(stdscr):
    stdscr.clear()
    stdscr.keypad(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

    fields = load_tree()
    update(stdscr, fields, None)

    fields[1].is_expanded = True
    update(stdscr, fields, stdscr.getkey())

    fields[1].fields[2].is_expanded = True
    update(stdscr, fields, stdscr.getkey())

    fields[1].fields[2].fields[4].is_selected = True
    update(stdscr, fields, stdscr.getkey())

    fields[1].fields[2].fields[3].is_expanded = True
    update(stdscr, fields, stdscr.getkey())

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

print(curses.wrapper(main))
