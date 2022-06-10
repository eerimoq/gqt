import curses
import os
import sys
from contextlib import contextmanager

from .cache import read_tree_from_cache
from .cache import write_tree_to_cache
from .endpoint import fetch_schema
from .screen import addstr
from .screen import move
from .tree import load_tree_from_schema


HELP_TEXT = '''\
Move:         <Left>, <Right>, <Up> and <Down>
Select:       <Space>
Execute:      <Enter>
Help:         h or ?
Quit:         <Ctrl-C>\
'''

HELP_NCOLS = 50


def format_title(kind, tree, description, x_max):
    if tree is not None:
        field_type = f' ─ {tree.cursor_type()}'
    else:
        field_type = ''

    line = f'╭─ {kind}{field_type}{description} '

    if len(line) >= x_max:
        line = line[:x_max - 3] + '...'

    return line


class QueryBuilder:

    def __init__(self, stdscr, endpoint, tree):
        self.stdscr = stdscr
        self.endpoint = endpoint
        self.tree = tree
        self.show_help = False
        self.y_offset = 1

    def draw(self, cursor, x_max, y):
        for i in range(y):
            self.addstr_frame(i, 0, '│')

        self.addstr(0, 0, ' ' * x_max)
        x_endpoint = (x_max - len(self.endpoint))
        self.addstr(0, x_endpoint, self.endpoint)
        description = self.tree.cursor_description()

        if description:
            description = description.split('\n')[0].strip()
            description = f' ─ {description}'
        else:
            description = ''

        if cursor.y_mutation == -1 or cursor.y < cursor.y_mutation:
            query_line = format_title('Query', self.tree, description, x_max)
            mutation_line = format_title('Mutation', None, '', x_max)
        else:
            query_line = format_title('Query', None, '', x_max)
            mutation_line = format_title('Mutation', self.tree, description, x_max)

        self.draw_title(0, query_line)

        if cursor.y_mutation != -1:
            self.addstr(cursor.y_mutation - 2, 0, ' ')
            self.draw_title(cursor.y_mutation - 1, mutation_line)

    def update_key(self, key):
        if key == 'KEY_UP':
            self.tree.key_up()
        elif key == 'KEY_DOWN':
            self.tree.key_down()
        elif key == 'KEY_LEFT':
            self.tree.key_left()
        elif key == 'KEY_RIGHT':
            self.tree.key_right()
        elif key == ' ':
            self.tree.select()
        elif key == '\n':
            return True
        elif key == 'KEY_RESIZE':
            pass
        elif key is not None:
            if not self.tree.key(key):
                if key in ['h', '?']:
                    self.show_help = not self.show_help

        return False

    def update(self, key):
        if self.update_key(key):
            return True
        elif self.show_help:
            self.draw_help()
        else:
            self.draw_selector()

        return False

    def draw_help(self):
        curses.curs_set(False)
        self.stdscr.erase()
        y_max, x_max = self.stdscr.getmaxyx()
        margin = (x_max - HELP_NCOLS) // 2
        text_col_left = margin + 2
        help_lines = HELP_TEXT.splitlines()
        horizontal_line = '─' * (HELP_NCOLS - 2)
        row = min((y_max - 6) // 2, y_max // 3)

        self.addstr_frame(row, margin, f'┌{horizontal_line}┐')
        self.addstr(row, margin + 1, ' Help ')
        row += 1

        for line in help_lines:
            self.addstr_frame(row, margin, '│')
            self.addstr_frame(row, margin + HELP_NCOLS - 1, '│')
            self.addstr(row, text_col_left, line)
            row += 1

        self.addstr_frame(row, margin, f'└{horizontal_line}┘')
        self.stdscr.refresh()

    def draw_selector(self):
        curses.curs_set(True)

        while True:
            self.stdscr.erase()
            y_max, x_max = self.stdscr.getmaxyx()
            y, cursor = self.tree.draw(self.stdscr, self.y_offset, 2)

            if cursor.y < 1:
                self.y_offset += 1
            elif cursor.y >= y_max:
                self.y_offset -= 1
            else:
                self.draw(cursor, x_max, y)
                break

        move(self.stdscr, cursor.y, cursor.x)
        self.stdscr.refresh()

    def run(self):
        self.stdscr.clear()
        self.stdscr.keypad(True)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_YELLOW, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)

        self.update(None)
        done = False

        while not done:
            try:
                key = self.stdscr.getkey()
            except curses.error:
                continue

            done = self.update(key)

    def addstr(self, y, x, text):
        addstr(self.stdscr, y, x, text)

    def addstr_frame(self, y, x, text):
        addstr(self.stdscr, y, x, text, curses.color_pair(3))

    def draw_title(self, y, line):
        x = 0
        parts = line.split(' ')
        self.addstr_frame(y, x, parts[0])
        x += 3
        self.addstr(y, x, parts[1])
        x += len(parts[1]) + 1

        if len(parts) > 2:
            self.addstr_frame(y, x, parts[2])
            x += 2
            self.addstr(y, x, ' '.join(parts[3:]))


def load_tree(endpoint, verify):
    try:
        return read_tree_from_cache(endpoint)
    except Exception:
        return load_tree_from_schema(fetch_schema(endpoint, verify))


def selector(stdscr, endpoint, tree):
    QueryBuilder(stdscr, endpoint, tree).run()


@contextmanager
def redirect_stdout_to_stderr():
    original_stdout = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

    try:
        yield
    finally:
        os.dup2(original_stdout, sys.stdout.fileno())
        os.close(original_stdout)


def query_builder(endpoint, verify):
    tree = load_tree(endpoint, verify)

    with redirect_stdout_to_stderr():
        curses.wrapper(selector, endpoint, tree)

    write_tree_to_cache(tree, endpoint)

    return tree
