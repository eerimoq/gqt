import curses
import sys

from readlike import edit

from .screen import addstr

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
                    self.fields[i].cursor = True

                    return CursorMove.DONE
                else:
                    return CursorMove.FOUND
            else:
                cursor_move = field.key_down()

                if cursor_move == CursorMove.FOUND:
                    if i < len(self.fields):
                        self.fields[i].cursor = True

                        return CursorMove.DONE
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
            sys.exit("No fields selected.")
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
