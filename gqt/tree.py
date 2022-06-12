import curses

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


def find_root_field(cursor):
    if cursor.parent is None:
        return cursor
    else:
        return find_root_field(cursor.parent)


def fields_query(fields):
    items = []
    arguments = []

    for field in fields:
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

    return ' '.join(items), arguments


class Cursor:

    def __init__(self):
        self.node = None
        self.y = 0
        self.x = 0
        self.y_mutation = None


class Node:

    def __init__(self):
        self.parent = None
        self.next = None
        self.prev = None
        self.type = None
        self.description = None

    def draw(self, stdscr, y, x, cursor):
        raise NotImplementedError()

    def key_left(self):
        return False

    def key_right(self):
        return False

    def select(self):
        pass

    def key(self, _key):
        return False

    def query(self):
        raise NotImplementedError()


class Object(Node):

    def __init__(self,
                 name,
                 field_type,
                 description,
                 fields,
                 number_of_query_fields,
                 is_root=False):
        super().__init__()
        self.name = name
        self.type = field_type
        self.description = description
        self.fields = fields

        if not is_root:
            self.fields.parent = self

        self.is_root = is_root
        self.number_of_query_fields = number_of_query_fields
        self.is_expanded = is_root

    def draw(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        if self.is_root:
            for i, field in enumerate(self.fields):
                if i == self.number_of_query_fields:
                    y += 2
                    cursor.y_mutation = y

                y = field.draw(stdscr, y, x, cursor)
        elif self.is_expanded:
            addstr(stdscr, y, x, '▼', curses.color_pair(1))
            addstr(stdscr, y, x + 2, self.name)
            y += 1

            for field in self.fields:
                y = field.draw(stdscr, y, x + 2, cursor)
        else:
            addstr(stdscr, y, x, '▶', curses.color_pair(1))
            addstr(stdscr, y, x + 2, self.name)
            y += 1

        return y

    def query(self):
        items, arguments = fields_query(self.fields)

        if items:
            return f'{self.name}{arguments} {{{items}}}'
        else:
            raise Exception(f"No fields selected in '{self.name}'.")

    def query_root(self, cursor):
        cursor_root_index = self.fields.index(find_root_field(cursor))
        is_query = (cursor_root_index < self.number_of_query_fields)

        if is_query:
            fields = self.fields[:self.number_of_query_fields]
        else:
            fields = self.fields[self.number_of_query_fields:]

        items, _ = fields_query(fields)

        if items:
            if is_query:
                kind = 'query Query'
            else:
                kind = 'mutation Mutation'

            return f"{kind} {{{items}}}"
        else:
            raise Exception("No fields selected.")


class Leaf(Node):

    def __init__(self, name, field_type, description):
        super().__init__()
        self.is_selected = False
        self.name = name
        self.type = field_type
        self.description = description

    def draw(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        if self.is_selected:
            addstr(stdscr, y, x, '■', curses.color_pair(1))
        else:
            addstr(stdscr, y, x, '□', curses.color_pair(1))

        addstr(stdscr, y, x + 2, self.name)

        return y + 1

    def select(self):
        self.is_selected = not self.is_selected


class Argument(Node):

    def __init__(self, name, field_type, description, state, types):
        super().__init__()
        self.name = name
        self._type = get_type(field_type)['name']
        self.type = get_type_string(field_type)
        self.description = description
        self.is_optional = (field_type['kind'] != 'NON_NULL')

        if self.is_optional:
            self.is_scalar = (field_type['kind'] == 'SCALAR')
        else:
            self.is_scalar = (field_type['ofType']['kind'] == 'SCALAR')

        self.state = state
        self.types = types
        self.value = ''
        self.pos = 0

        if self.is_optional:
            self.symbol = '□'
        else:
            self.symbol = '■'

    def is_string(self):
        return self.is_scalar and self._type in ['String', 'ID']

    def draw(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y

            if self.state.cursor_at_input_field:
                cursor.x = x + len(self.name) + 4 + self.pos
            else:
                cursor.x = x

        addstr(stdscr, y, x, self.symbol, curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        addstr(stdscr,
               y,
               x + 2 + len(self.name) + 2,
               self.value,
               curses.color_pair(2))

        return y + 1

    def next_symbol(self):
        if self.is_optional:
            table = {
                '□': '■',
                '■': '□'
            }
        else:
            table = {
                '■': '■'
            }

        self.symbol = table[self.symbol]

    def key_left(self):
        if self.state.cursor_at_input_field:
            self.key('KEY_LEFT')

            return True
        else:
            return False

    def key_right(self):
        if self.state.cursor_at_input_field:
            self.key('KEY_RIGHT')

            return True
        else:
            return False

    def key(self, key):
        if key == '\t':
            self.state.cursor_at_input_field = not self.state.cursor_at_input_field

            return True
        elif self.state.cursor_at_input_field:
            self.value, self.pos = edit(self.value,
                                        self.pos,
                                        KEY_BINDINGS.get(key, key))

            return True

        return False

    def select(self):
        if self.state.cursor_at_input_field:
            self.key(' ')
        else:
            self.next_symbol()

    def query(self):
        if self.symbol == '■':
            if self.is_string():
                return f'"{self.value}"'
            else:
                return str(self.value)
        elif self.symbol == '□':
            return None
        elif self.symbol == '$':
            return f'${self.value}'
        else:
            return 'null'

class State:

    def __init__(self):
        self.cursor_at_input_field = False


def find_type(types, name):
    for type_info in types:
        if type_info['name'] == name:
            return type_info

    raise Exception(f"Type '{name}' not found in schema.")


def get_type(type_info):
    while type_info['kind'] in ['NON_NULL', 'LIST']:
        type_info = type_info['ofType']

    return type_info


def get_type_string(type_info):
    kind = type_info['kind']

    if kind == 'NON_NULL':
        return f"{get_type_string(type_info['ofType'])}!"
    elif kind == 'LIST':
        return f"[{get_type_string(type_info['ofType'])}]"
    else:
        return type_info['name']


def build_field(types, field, state):
    try:
        name = field['name']
    except Exception:
        raise Exception("No field name.")

    item = get_type(field['type'])
    field_type = item['name']
    field_type_string = get_type_string(field['type'])
    description = field['description']

    if item['kind'] == 'OBJECT':
        fields = find_type(types, field_type)['fields']

        return Object(name,
                      field_type_string,
                      description,
                      ObjectFields(field['args'], fields, types, state),
                      len(fields))
    else:
        return Leaf(name, field_type_string, description)


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

    def __init__(self, arguments, fields, types, state):
        self._arguments_info = arguments
        self._fields_info = fields
        self._types = types
        self._state = state
        self._fields = None
        self.parent = None

    def fields(self):
        if self._fields is None:
            self._fields = [
                Argument(arg['name'],
                         arg['type'],
                         arg['description'],
                         self._state,
                         self._types)
                for arg in self._arguments_info
            ] + [
                build_field(self._types, field, self._state)
                for field in self._fields_info
            ]

        for field in self._fields:
            field.parent = self.parent

        if len(self._fields) > 1:
            for i in range(len(self._fields)):
                if i > 0:
                    self._fields[i - 1].next = self._fields[i]
                    self._fields[i].prev = self._fields[i - 1]

        return self._fields

    def __iter__(self):
        return ObjectFieldsIterator(self.fields())

    def __len__(self):
        return len(self.fields())

    def index(self, item):
        return self.fields().index(item)

    def __getitem__(self, key):
        return self.fields()[key]


class Tree:

    def __init__(self, root):
        self._root = root
        self._cursor = root.fields[0]

    def cursor_type(self):
        return self._cursor.type

    def cursor_description(self):
        return self._cursor.description

    def draw(self, stdscr, y, x):
        cursor = Cursor()
        cursor.node = self._cursor

        return self._root.draw(stdscr, y, x, cursor), cursor

    def key_up(self):
        if self._cursor.prev is not None:
            self._cursor = self._find_last(self._cursor.prev)
        elif self._cursor.parent is not None:
            self._cursor = self._cursor.parent

    def key_down(self):
        if isinstance(self._cursor, Object):
            if self._cursor.is_expanded:
                self._cursor = self._cursor.fields[0]
                return

        if self._cursor.next is not None:
            self._cursor = self._cursor.next
        elif self._cursor.parent is not None:
            cursor = self._find_first_below(self._cursor)

            if cursor is not None:
                self._cursor = cursor

    def key_left(self):
        if self._cursor.key_left():
            return

        if isinstance(self._cursor, Object):
            if self._cursor.is_expanded:
                self._cursor.is_expanded = False
                return

        if self._cursor.parent is not None:
            self._cursor = self._cursor.parent

    def key_right(self):
        if self._cursor.key_right():
            return

        if isinstance(self._cursor, Object):
            if self._cursor.is_expanded:
                self._cursor = self._cursor.fields[0]
            else:
                self._cursor.is_expanded = True

    def select(self):
        self._cursor.select()

    def key(self, key):
        return self._cursor.key(key)

    def query(self):
        return self._root.query_root(self._cursor)

    def go_to_begin(self):
        self._cursor = self._root.fields[0]

    def go_to_end(self):
        self._cursor = self._find_last(self._root.fields[-1])

    def _find_first_below(self, node):
        if node.parent is not None:
            if node.parent.next is not None:
                return node.parent.next
            else:
                return self._find_first_below(node.parent)
        else:
            return None

    def _find_last(self, node):
        if isinstance(node, Object):
            if node.is_expanded:
                return self._find_last(node.fields[-1])
            else:
                return node
        else:
            return node


def load_tree_from_schema(schema):
    types = schema['__schema']['types']
    query_type = schema['__schema']['queryType']

    if query_type is not None:
        query_fields = find_type(types, query_type['name'])['fields']
    else:
        query_fields = []

    mutation_type = schema['__schema']['mutationType']

    if mutation_type is not None:
        mutation_fields = find_type(types, mutation_type['name'])['fields']
    else:
        mutation_fields = []

    state = State()
    tree = Object(None,
                  '',
                  None,
                  ObjectFields([], query_fields + mutation_fields, types, state),
                  len(query_fields),
                  True)
    tree.fields[0].cursor = True

    return Tree(tree)
