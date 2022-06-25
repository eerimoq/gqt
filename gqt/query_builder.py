import curses
import os
import sys
from contextlib import contextmanager

from graphql.language import parse

from .cache import read_tree_from_cache
from .cache import write_tree_to_cache
from .endpoint import fetch_schema
from .experimental import is_experimental
from .screen import addstr
from .screen import move
from .tree import load_tree_from_schema

HELP_TEXT = '''\
Move:              <Left>, <Right>, <Up> and <Down>
                   <Page-Up> and <Page-Down>
                   <Meta-<> and <Meta->>
                   <Tab>
Select:            <Space>
Variable:          v or $
{compact}\
Delete list item:  <Backspace>
Execute:           <Enter>
Reload schema:     r
Help:              h or ?
Quit:              q or <Ctrl-C>\
'''

HELP_NCOLS = 55


def help_text():
    if is_experimental():
        compact = 'Compact:           c\n'
    else:
        compact = ''

    return HELP_TEXT.format(compact=compact)


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

    def __init__(self, stdscr, endpoint, query_name, headers, verify):
        self.stdscr = stdscr
        self.endpoint = endpoint
        self.query_name = query_name
        self.headers = headers
        self.verify = verify
        self.show_help = False
        self.y_offset = 1
        self.error = None
        self.meta = False

        try:
            self.tree = read_tree_from_cache(endpoint, query_name)
            self.show_fetching_schema = False
        except Exception:
            self.tree = None
            self.show_fetching_schema = True

    def draw(self, cursor, y_max, x_max, y):
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

        if cursor.y_mutation is None or cursor.y < cursor.y_mutation:
            query_line = format_title('Query', self.tree, description, x_max)
            mutation_line = format_title('Mutation', None, '', x_max)
        else:
            query_line = format_title('Query', None, '', x_max)
            mutation_line = format_title('Mutation', self.tree, description, x_max)

        self.draw_title(0, query_line)

        if cursor.y_mutation is not None:
            self.addstr(max(cursor.y_mutation - 2, 0), 0, ' ')
            self.draw_title(max(cursor.y_mutation - 1, 0), mutation_line)

        self.addstr(y_max - 1, 0, ' ' * x_max)

        if self.error is not None:
            self.addstr_error(y_max - 1, 0, self.error)
            self.error = None

    def update_key(self, key):
        if key == curses.KEY_UP:
            self.tree.key_up()
        elif key == curses.KEY_DOWN:
            self.tree.key_down()
        elif key == curses.KEY_LEFT:
            self.tree.key_left()
        elif key == curses.KEY_RIGHT:
            self.tree.key_right()
        elif key == curses.KEY_PPAGE:
            for _ in range(self.page_up_down_lines()):
                self.tree.key_up()
        elif key == curses.KEY_NPAGE:
            for _ in range(self.page_up_down_lines()):
                self.tree.key_down()
        elif key == ' ':
            self.tree.select()
        elif key == '\n':
            return True
        elif key == curses.KEY_RESIZE:
            pass
        elif self.meta:
            self.meta = False

            if key == '<':
                self.tree.go_to_begin()
            elif key == '>':
                self.tree.go_to_end()
            else:
                self.tree.key('\x1b' + key)
        elif key == '\x1b':
            self.meta = True
        elif key is not None:
            if isinstance(key, int):
                key = curses.keyname(key).decode()

            if not self.tree.key(key):
                if key in ['h', '?']:
                    self.show_help = not self.show_help
                elif key == 'r':
                    self.show_fetching_schema = True
                elif key == 'c':
                    if is_experimental():
                        self.tree.toggle_compact()
                elif key == 'q':
                    raise KeyboardInterrupt()

        return False

    def update_key_help(self, key):
        if key in ['h', '?']:
            self.show_help = not self.show_help
        elif key == 'q':
            raise KeyboardInterrupt()

    def update(self, key):
        if self.show_help:
            self.update_key_help(key)
        else:
            if self.update_key(key):
                try:
                    parse(self.tree.query())

                    return True
                except Exception as error:
                    self.error = str(error)

        if self.show_fetching_schema:
            self.draw_fetching_schema()
            self.show_fetching_schema = False

        if self.show_help:
            self.draw_help()
        else:
            self.draw_selector()

        return False

    def draw_fetching_schema(self):
        curses.curs_set(False)
        self.stdscr.erase()
        message = f"Fetching schema from '{self.endpoint}'..."
        y_max, x_max = self.stdscr.getmaxyx()
        col = max((x_max - len(message) - 4) // 2, 0)
        row = min((y_max - 6) // 2, y_max // 3)
        horizontal_line = '─' * len(message)
        horizontal_space = ' ' * len(message)

        self.addstr_frame(row + 0, col, f'┌─{horizontal_line}─┐')
        self.addstr_frame(row + 1, col, f'│ {horizontal_space} │')
        self.addstr_frame(row + 2, col, f'│ {horizontal_space} │')
        self.addstr(row + 2, col + 2, message)
        self.addstr_frame(row + 3, col, f'│ {horizontal_space} │')
        self.addstr_frame(row + 4, col, f'└─{horizontal_line}─┘')
        self.stdscr.refresh()
        self.tree = load_tree_from_schema(
            fetch_schema(self.endpoint, self.headers, self.verify))

    def draw_help(self):
        curses.curs_set(False)
        self.stdscr.erase()
        y_max, x_max = self.stdscr.getmaxyx()
        margin = (x_max - HELP_NCOLS) // 2
        text_col_left = margin + 2
        help_lines = help_text().splitlines()
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

            if y == self.y_offset:
                self.draw(cursor, y_max, x_max, y)
                break

            if cursor.y < 1:
                self.y_offset += 10

                if self.y_offset > 1:
                    self.y_offset = 1
            elif cursor.y >= y_max - 1:
                self.y_offset -= min(10, y - cursor.y)
            else:
                self.draw(cursor, y_max, x_max, y)
                break

        if cursor.y == 0:
            curses.curs_set(False)
        else:
            curses.curs_set(True)
            move(self.stdscr, cursor.y, cursor.x)

        self.stdscr.refresh()

    def run(self):
        self.stdscr.clear()
        self.stdscr.keypad(True)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_YELLOW, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, -1, curses.COLOR_MAGENTA)
        curses.init_pair(6, -1, curses.COLOR_GREEN)

        try:
            self.update(None)
            done = False

            while not done:
                try:
                    key = self.stdscr.get_wch()
                except curses.error:
                    continue

                done = self.update(key)
        finally:
            if self.tree is not None:
                write_tree_to_cache(self.tree, self.endpoint, self.query_name)

        return self.tree

    def addstr(self, y, x, text):
        addstr(self.stdscr, y, x, text)

    def addstr_frame(self, y, x, text):
        addstr(self.stdscr, y, x, text, curses.color_pair(3))

    def addstr_error(self, y, x, text):
        addstr(self.stdscr,
               y,
               x,
               text,
               curses.color_pair(4) | curses.A_BOLD)

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

    def page_up_down_lines(self):
        return 10


def selector(stdscr, endpoint, query_name, headers, verify):
    return QueryBuilder(stdscr, endpoint, query_name, headers, verify).run()


@contextmanager
def redirect_stdout_to_stderr():
    original_stdout = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

    try:
        yield
    finally:
        os.dup2(original_stdout, sys.stdout.fileno())
        os.close(original_stdout)


def query_builder(endpoint, query_name, headers, verify):
    with redirect_stdout_to_stderr():
        return curses.wrapper(selector, endpoint, query_name, headers, verify)
