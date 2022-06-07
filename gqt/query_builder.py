import curses
import os
import sys
from contextlib import contextmanager

import requests
from graphql import get_introspection_query

from .cache import read_tree_from_cache
from .cache import write_tree_to_cache
from .screen import addstr
from .screen import move
from .tree import load_tree_from_schema


def format_title(kind, tree, description, x_max):
    if tree is not None:
        field_type = f' ─ {tree.cursor_type()}'
    else:
        field_type = ''

    line = f'╭─ {kind}{field_type}{description} '

    if len(line) >= x_max:
        line = line[:x_max - 3] + '...'

    return line


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

    while True:
        stdscr.erase()
        y_max, x_max = stdscr.getmaxyx()
        y, cursor = tree.show(stdscr, y_offset, 2)

        if cursor.y < 1:
            y_offset += 1
        elif cursor.y >= y_max:
            y_offset -= 1
        else:
            for i in range(y):
                addstr(stdscr, i, 0, '│')

            addstr(stdscr, 0, 0, ' ' * x_max)
            x_endpoint = (x_max - len(endpoint))
            addstr(stdscr, 0, x_endpoint, endpoint)
            description = tree.cursor_description()

            if description:
                description = description.split('\n')[0].strip()
                description = f' ─ {description}'
            else:
                description = ''

            if cursor.y_mutation == -1 or cursor.y < cursor.y_mutation:
                query_line = format_title('Query', tree, description, x_max)
                mutation_line = format_title('Mutation', None, '', x_max)
            else:
                query_line = format_title('Query', None, '', x_max)
                mutation_line = format_title('Mutation', tree, description, x_max)

            addstr(stdscr, 0, 0, query_line)

            if cursor.y_mutation != -1:
                addstr(stdscr, cursor.y_mutation - 2, 0, ' ')
                addstr(stdscr, cursor.y_mutation - 1, 0, mutation_line)

            break

    move(stdscr, cursor.y, cursor.x)
    stdscr.refresh()

    return False, y_offset


def fetch_schema(endpoint, verify):
    response = post(endpoint, {"query": get_introspection_query()}, verify)
    response = response.json()

    if 'errors' in response:
        sys.exit(response['errors'])

    return response['data']


def load_tree(endpoint, verify):
    try:
        return read_tree_from_cache(endpoint)
    except Exception:
        return load_tree_from_schema(fetch_schema(endpoint, verify))


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


def post(endpoint, query, verify):
    response = requests.post(endpoint, json=query, verify=verify)

    if response.status_code != 200:
        print(response.text, file=sys.stderr)
        response.raise_for_status()

    return response
