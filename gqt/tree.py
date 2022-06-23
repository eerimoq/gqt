import curses

from readlike import edit

from .screen import addstr

KEY_BINDINGS = {
    'KEY_BACKSPACE': 'backspace',
    '\b': 'backspace',
    'KEY_DC': 'backspace',
    '\x7f': 'backspace',
    '\x01': 'ctrl a',
    '\x04': 'ctrl d',
    '\x05': 'ctrl e',
    '\x0b': 'ctrl k',
    '\x14': 'ctrl t',
    'KEY_LEFT': 'left',
    '\x1b\x7f': 'meta backspace',
    '\x1bd': 'meta d',
    'kLFT5': 'meta left',
    'kRIT5': 'meta right',
    'KEY_RIGHT': 'right'
}

OPTIONAL_SYMBOLS = {
    '□': '■',
    '■': '□'
}


def query_variable(value, value_type, variables):
    if value:
        value = f'${value}'
        variables.append((value, value_type))

        return value
    else:
        raise Exception('Missing variable name.')


def find_root_field(cursor):
    if cursor.parent is None:
        return cursor
    else:
        return find_root_field(cursor.parent)


def fields_query(fields, variables, is_union=False):
    items = []
    arguments = []

    for field in fields:
        value = field.query(variables)

        if value is None:
            continue

        if isinstance(field,
                      (ScalarArgument, InputArgument, ListArgument, EnumArgument)):
            arguments.append(f'{field.name}:{value}')
        elif is_union:
            items.append(f'... on {value}')
        else:
            items.append(value)

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
        self.child = None
        self.next = None
        self.prev = None
        self.type = None
        self.description = None

    def is_match(self):
        return False

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

    def query(self, variables):
        raise NotImplementedError()

    def make_compact(self):
        pass

    def make_not_compact(self):
        pass

    def is_selected(self):
        return False


class Object(Node):

    def __init__(self,
                 name,
                 field_type,
                 description,
                 fields,
                 state,
                 number_of_query_fields,
                 is_root=False,
                 is_union=False):
        super().__init__()
        self.name = name
        self.type = field_type
        self.description = description
        self.fields = fields
        self.state = state

        if not is_root:
            self.fields.parent = self

        self.is_root = is_root
        self.is_union = is_union
        self.number_of_query_fields = number_of_query_fields
        self.is_expanded = is_root

    def is_match(self):
        if self.is_root:
            return False
        else:
            return self.state.search.is_match(self.name)

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
            self.state.search.draw(stdscr, y, x + 2, self.name, self)
            y += 1

            for field in self.fields:
                y = field.draw(stdscr, y, x + 2, cursor)
        else:
            addstr(stdscr, y, x, '▶', curses.color_pair(1))
            self.state.search.draw(stdscr, y, x + 2, self.name, self)
            y += 1

        return y

    def query(self, variables):
        if not self.is_expanded:
            return None

        items, arguments = fields_query(self.fields, variables, self.is_union)

        if items:
            if self.is_union:
                return f'{self.name}{arguments} {{__typename {items}}}'
            else:
                return f'{self.name}{arguments} {{{items}}}'
        else:
            raise Exception(f"No fields selected in '{self.name}'.")

    def key_left(self):
        if not self.is_expanded:
            return False

        self.is_expanded = False
        self.child = None

        return True

    def key_right(self):
        if self.is_expanded:
            return False
        else:
            self.is_expanded = True
            self.child = self.fields[0]

            return True

    def query_root(self, cursor):
        cursor_root_index = self.fields.index(find_root_field(cursor))
        is_query = (cursor_root_index < self.number_of_query_fields)

        if is_query:
            fields = self.fields[:self.number_of_query_fields]
        else:
            fields = self.fields[self.number_of_query_fields:]

        variables = []
        items, _ = fields_query(fields, variables)

        if items:
            if variables:
                variables = '(' + ','.join([
                    f'{name}:{value}'
                    for name, value in variables
                ]) + ')'
            else:
                variables = ''

            if is_query:
                kind = 'query Query'
            else:
                kind = 'mutation Mutation'

            return f"{kind}{variables} {{{items}}}"
        else:
            raise Exception("No fields selected.")

    def select(self):
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.child = self.fields[0]
        else:
            self.child = None

    def is_selected(self):
        if not self.is_expanded:
            return False

        for field in self.fields:
            if field.is_selected():
                return True

        return False

    def make_compact(self):
        self.fields.make_compact()

        if self.is_expanded and len(self.fields) > 0:
            self.child = self.fields[0]
        else:
            self.child = None

    def make_not_compact(self):
        self.fields.make_not_compact()

        if self.is_expanded and len(self.fields) > 0:
            self.child = self.fields[0]
        else:
            self.child = None


class Leaf(Node):

    def __init__(self, name, field_type, description, fields, state):
        super().__init__()
        self._is_selected = False
        self.name = name
        self.type = field_type
        self.description = description
        self.fields = fields
        self.state = state

        if self.fields is not None:
            self.fields.parent = self

    def is_match(self):
        return self.state.search.is_match(self.name)

    def draw(self, stdscr, y, x, cursor):
        if self.fields is None:
            return self.draw_without_arguments(stdscr, y, x, cursor)
        else:
            return self.draw_with_arguments(stdscr, y, x, cursor)

    def draw_with_arguments(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        self.state.search.draw(stdscr, y, x + 2, self.name, self)

        if self._is_selected:
            addstr(stdscr, y, x, '■', curses.color_pair(1))
            y += 1

            for field in self.fields:
                y = field.draw(stdscr, y, x + 2, cursor)
        else:
            addstr(stdscr, y, x, '□', curses.color_pair(1))
            y += 1

        return y

    def draw_without_arguments(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        if self._is_selected:
            addstr(stdscr, y, x, '■', curses.color_pair(1))
        else:
            addstr(stdscr, y, x, '□', curses.color_pair(1))

        self.state.search.draw(stdscr, y, x + 2, self.name, self)

        return y + 1

    def select(self):
        self._is_selected = not self._is_selected

        if self.fields is not None:
            if self._is_selected:
                self.child = self.fields[0]
            else:
                self.child = None

    def query(self, variables):
        if not self._is_selected:
            return None

        if self.fields is None:
            arguments = ''
        else:
            arguments = fields_query(self.fields, variables)[1]

        return f'{self.name}{arguments}'

    def is_selected(self):
        return self._is_selected


class ScalarArgument(Node):

    def __init__(self,
                 name,
                 field_type,
                 description,
                 state,
                 types):
        super().__init__()
        self.name = name
        self._type = get_type(field_type)['name']
        self.type = get_type_string(field_type)
        self.description = description
        self.is_optional = (field_type['kind'] != 'NON_NULL')
        self.is_variable = False

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
            self.symbol = '●'

    def is_string(self):
        return self.is_scalar and self._type in ['String', 'ID']

    def draw(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y

            if self.state.cursor_at_input_field:
                cursor.x = x + len(self.name) + 4 + self.pos
            else:
                cursor.x = x

        if self.is_variable:
            symbol = '$'
        else:
            symbol = self.symbol

        addstr(stdscr, y, x, symbol, curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        addstr(stdscr,
               y,
               x + 2 + len(self.name) + 2,
               self.value,
               curses.color_pair(2))

        return y + 1

    def key_left(self):
        return self.key_left_right('KEY_LEFT')

    def key_right(self):
        return self.key_left_right('KEY_RIGHT')

    def key_left_right(self, key):
        if self.state.cursor_at_input_field:
            self.key(key)

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
        elif key in 'v$':
            self.is_variable = not self.is_variable

            return True

        return False

    def select(self):
        if self.state.cursor_at_input_field:
            self.key(' ')
        elif self.is_optional and not self.is_variable:
            self.symbol = OPTIONAL_SYMBOLS[self.symbol]

    def query(self, variables):
        if self.is_variable:
            return query_variable(self.value, self.type, variables)
        elif self.symbol in '■●':
            if self.is_string():
                return f'"{self.value}"'
            elif self.value:
                if self._type == 'Int':
                    try:
                        int(self.value, 10)
                    except Exception:
                        raise Exception(f"'{self.value}' is not an integer.")
                elif self._type == 'Float':
                    try:
                        float(self.value)
                    except Exception:
                        raise Exception(f"'{self.value}' is not a float.")
                elif self._type == 'Boolean':
                    if self.value not in ['true', 'false']:
                        raise Exception(
                            f"Boolean must be 'true' or 'false', "
                            f"not '{self.value}'.")

                return self.value
            else:
                raise Exception('Missing scalar value.')
        else:
            return None

    def is_selected(self):
        return self.is_variable or self.symbol in '■●'


class EnumArgument(Node):

    def __init__(self,
                 name,
                 field_type,
                 description,
                 state,
                 types):
        super().__init__()
        self.name = name
        self.type = get_type_string(field_type)
        self.description = description
        self.is_optional = (field_type['kind'] != 'NON_NULL')
        self.is_variable = False

        if not self.is_optional:
            field_type = field_type['ofType']

        self.members = [
            value['name']
            for value in find_type(types, field_type['name'])['enumValues']
        ]
        self.state = state
        self.value = ''
        self.pos = 0

        if self.is_optional:
            self.symbol = '□'
        else:
            self.symbol = '●'

    def draw(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y

            if self.state.cursor_at_input_field:
                cursor.x = x + len(self.name) + 4 + self.pos
            else:
                cursor.x = x

        if self.is_variable:
            symbol = '$'
        else:
            symbol = self.symbol

        addstr(stdscr, y, x, symbol, curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        addstr(stdscr,
               y,
               x + 2 + len(self.name) + 2,
               self.value,
               curses.color_pair(2))

        if not self.is_variable:
            x += (2 + len(self.name + self.value) + 3)

            if self.value not in self.members:
                _, x_max = stdscr.getmaxyx()
                members = [
                    member
                    for member in self.members
                    if member.startswith(self.value)
                ]
                members = '(' + ', '.join(members) + ')'
                members = members[:max(x_max - x, 0)]
                addstr(stdscr, y, x, members)

        return y + 1

    def key_left(self):
        return self.key_left_right('KEY_LEFT')

    def key_right(self):
        return self.key_left_right('KEY_RIGHT')

    def key_left_right(self, key):
        if self.state.cursor_at_input_field:
            self.key(key)

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
        elif key in 'v$':
            self.is_variable = not self.is_variable

            return True

        return False

    def select(self):
        if self.state.cursor_at_input_field:
            self.key(' ')
        elif self.is_optional and not self.is_variable:
            self.symbol = OPTIONAL_SYMBOLS[self.symbol]

    def query(self, variables):
        if self.is_variable:
            return query_variable(self.value, self.type, variables)
        elif self.symbol in '■●':
            if self.value:
                if self.value in self.members:
                    return str(self.value)
                else:
                    raise Exception(f"Invalid enum value '{self.value}'.")
            else:
                raise Exception('Missing enum value.')
        else:
            return None

    def is_selected(self):
        return self.is_variable or self.symbol in '■●'


class InputArgument(Node):

    def __init__(self,
                 name,
                 field_type,
                 description,
                 state,
                 types):
        super().__init__()
        self.name = name
        self._type = get_type(field_type)['name']
        self.type = get_type_string(field_type)
        self.description = description
        self.is_optional = (field_type['kind'] != 'NON_NULL')
        self.is_variable = False
        self.state = state
        self.types = types
        self.value = ''
        self.pos = 0

        if self.is_optional:
            fields = find_type(types, field_type['name'])['inputFields']
        else:
            fields = find_type(types, field_type['ofType']['name'])['inputFields']

        self.fields = ObjectFields(fields, [], types, state)
        self.fields.parent = self

        if self.is_optional:
            self.symbol = '□'
        else:
            self.symbol = '●'
            self.child = self.fields[0]

    def draw_variable(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y

            if self.state.cursor_at_input_field:
                cursor.x = x + len(self.name) + 4 + self.pos
            else:
                cursor.x = x

        addstr(stdscr, y, x, '$', curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        addstr(stdscr,
               y,
               x + 2 + len(self.name) + 2,
               self.value,
               curses.color_pair(2))

        return y + 1

    def draw_members(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        addstr(stdscr, y, x, self.symbol, curses.color_pair(3))
        x += 2
        addstr(stdscr, y, x, f'{self.name}:')
        y += 1

        if self.symbol in '■●':
            for field in self.fields:
                y = field.draw(stdscr, y, x, cursor)

        return y

    def draw(self, stdscr, y, x, cursor):
        if self.is_variable:
            return self.draw_variable(stdscr, y, x, cursor)
        else:
            return self.draw_members(stdscr, y, x, cursor)

    def key_left(self):
        return self.key_left_right('KEY_LEFT')

    def key_right(self):
        return self.key_left_right('KEY_RIGHT')

    def key_left_right(self, key):
        if self.state.cursor_at_input_field:
            self.key(key)

            return True
        else:
            return False

    def key(self, key):
        if self.is_variable:
            if key == '\t':
                self.state.cursor_at_input_field = (
                    not self.state.cursor_at_input_field)

                return True
            elif self.state.cursor_at_input_field:
                self.value, self.pos = edit(self.value,
                                            self.pos,
                                            KEY_BINDINGS.get(key, key))

                return True
            elif key in 'v$':
                return self.key_variable()
        elif key in 'v$':
            return self.key_variable()

        return False

    def key_variable(self):
        self.is_variable = not self.is_variable

        if self.is_variable:
            self.child = None
        elif self.symbol != '□':
            self.child = self.fields[0]

        return True

    def select(self):
        if self.is_optional and not self.is_variable:
            self.symbol = OPTIONAL_SYMBOLS[self.symbol]

            if self.symbol == '■':
                self.child = self.fields[0]
            else:
                self.child = None

    def query(self, variables):
        if self.is_variable:
            return query_variable(self.value, self.type, variables)
        elif self.symbol in '■●':
            items = []

            for field in self.fields:
                value = field.query(variables)

                if value is not None:
                    items.append(f'{field.name}:{value}')

            return '{' + ','.join(items) + '}'
        else:
            return None
#
#     def is_selected(self):
#         if self.is_variable:
#             return True
#
#         if self.symbol not in '■●':
#             return False
#
#         for field in self.fields:
#             if field.is_selected():
#                 return True
#
#         return False
#
#     def make_compact(self):
#         self.fields.make_compact()
#
#         if self.is_variable:
#             self.child = None
#         elif self.symbol != '□' and len(self.fields) > 0:
#             self.child = self.fields[0]
#         else:
#             self.child = None
#
#     def make_not_compact(self):
#         self.fields.make_not_compact()
#
#         if self.is_variable:
#             self.child = None
#         elif self.symbol != '□' and len(self.fields) > 0:
#             self.child = self.fields[0]
#         else:
#             self.child = None


class ListItem(Node):

    def __init__(self, item, item_type):
        super().__init__()
        self.type = get_type_string(item_type)
        self.is_expanded = False
        self.item = item
        self.item.parent = self
        self.removed = False

    def draw_item(self, stdscr, y, x, i, number_of_items, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        if self.is_expanded:
            symbol = '▼'
        else:
            symbol = '▶'

        addstr(stdscr, y, x, symbol, curses.color_pair(3))
        x += 2

        if i < (number_of_items - 1):
            addstr(stdscr, y, x, f'[{i}]')
            y += 1

            if self.is_expanded:
                y = self.item.draw(stdscr, y, x, cursor)
        else:
            addstr(stdscr, y, x, '...')
            y += 1

        return y

    def key(self, key):
        if KEY_BINDINGS.get(key) == 'backspace' and self is not self.parent.items[-1]:
            self.removed = True
            self.parent.item_removed(self)

            return True

        return False

    def key_left(self):
        if not self.is_expanded:
            return False

        self.is_expanded = False
        self.child = None

        return True

    def key_right(self):
        if self.is_expanded:
            return False
        else:
            self.is_expanded = True
            self.child = self.item
            self.parent.item_selected(self)

            return True

    def select(self):
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.child = self.item
            self.parent.item_selected(self)
        else:
            self.child = None

    def query(self, variables):
        if not self.is_expanded:
            return None

        value = self.item.query(variables)

        if value is None:
            value = 'null'

        return value


class ListArgument(Node):

    def __init__(self,
                 name,
                 field_type,
                 description,
                 state,
                 types):
        super().__init__()
        self.name = name
        self.type = get_type_string(field_type)
        self.description = description
        self.is_optional = (field_type['kind'] != 'NON_NULL')
        self.is_variable = False
        self.state = state
        self.field_type = field_type
        self.types = types
        self.value = ''
        self.pos = 0

        if self.is_optional:
            self.symbol = '□'
        else:
            self.symbol = '●'

        self.items = []
        self.append_item()

        if self.symbol == '●':
            self.child = self.items[0]

    def append_item(self):
        if self.is_optional:
            item_type = self.field_type['ofType']
        else:
            item_type = self.field_type['ofType']['ofType']

        arg_type = {
            'name': 'value',
            'description': '',
            'type': item_type
        }
        item = ListItem(build_argument(arg_type, self.types, self.state),
                        item_type)

        if len(self.items) > 0:
            self.items[-1].next = item
            item.prev = self.items[-1]

        item.parent = self

        self.items.append(item)

    def draw_variable(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y

            if self.state.cursor_at_input_field:
                cursor.x = x + len(self.name) + 4 + self.pos
            else:
                cursor.x = x

        addstr(stdscr, y, x, '$', curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        addstr(stdscr,
               y,
               x + 2 + len(self.name) + 2,
               self.value,
               curses.color_pair(2))

        return y + 1

    def draw_items(self, stdscr, y, x, cursor):
        if cursor.node is self:
            cursor.y = y
            cursor.x = x

        addstr(stdscr, y, x, self.symbol, curses.color_pair(3))
        addstr(stdscr, y, x + 2, f'{self.name}:')
        y += 1

        if self.symbol in '■●':
            for i, item in enumerate(self.items):
                y = item.draw_item(stdscr, y, x + 2, i, len(self.items), cursor)

        return y

    def draw(self, stdscr, y, x, cursor):
        if self.is_variable:
            return self.draw_variable(stdscr, y, x, cursor)
        else:
            return self.draw_items(stdscr, y, x, cursor)

    def item_selected(self, item):
        if item is self.items[-1]:
            self.append_item()

    def item_removed(self, item):
        self.items.remove(item)

        if item.prev is not None:
            item.prev.next = item.next
        else:
            self.child = item.next

        if item.next is not None:
            item.next.prev = item.prev

    def select(self):
        if self.is_optional and not self.is_variable:
            self.symbol = OPTIONAL_SYMBOLS[self.symbol]

            if self.symbol == '■':
                self.child = self.items[0]
            else:
                self.child = None

    def key(self, key):
        if self.is_variable:
            if key == '\t':
                self.state.cursor_at_input_field = (
                    not self.state.cursor_at_input_field)

                return True
            elif self.state.cursor_at_input_field:
                self.value, self.pos = edit(self.value,
                                            self.pos,
                                            KEY_BINDINGS.get(key, key))

                return True
            elif key in 'v$':
                return self.key_variable()
        elif key in 'v$':
            return self.key_variable()

        return False

    def key_variable(self):
        self.is_variable = not self.is_variable

        if self.is_variable:
            self.child = None
        elif self.symbol != '□':
            self.child = self.items[0]

        return True

    def query(self, variables):
        if self.is_variable:
            if self.value:
                value = f'${self.value}'
                variables.append((value, self.type))

                return value
            else:
                raise Exception('Missing variable name.')
        elif self.symbol in '■●':
            items = []

            for item in self.items:
                value = item.query(variables)

                if value is not None:
                    items.append(value)

            return f'[{", ".join(items)}]'
        else:
            return None


class State:

    def __init__(self):
        self.cursor_at_input_field = False
        self.compact = False
        self.search = None


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


def build_field(field, types, state):
    try:
        name = field['name']
    except Exception:
        raise Exception("No field name.")

    item = get_type(field['type'])
    field_type = item['name']
    field_type_string = get_type_string(field['type'])
    description = field['description']

    if item['kind'] in ['OBJECT', 'INTERFACE']:
        fields = find_type(types, field_type)['fields']

        return Object(name,
                      field_type_string,
                      description,
                      ObjectFields(field['args'], fields, types, state),
                      state,
                      len(fields))
    elif item['kind'] == 'UNION':
        fields = [
            {
                'name': field['name'],
                'description': '',
                'args': [],
                'type': find_type(types, field['name'])
            }
            for field in find_type(types, field_type)['possibleTypes']
        ]

        return Object(name,
                      field_type_string,
                      description,
                      ObjectFields(field['args'], fields, types, state),
                      state,
                      len(fields),
                      is_union=True)
    else:
        if field['args']:
            fields = ObjectFields(field['args'], [], types, state)
        else:
            fields = None

        return Leaf(name, field_type_string, description, fields, state)


def build_argument(argument, types, state):
    name = argument['name']
    description = argument['description']
    arg_type = argument['type']
    kind = arg_type['kind']

    if kind == 'NON_NULL':
        kind = arg_type['ofType']['kind']

    if kind == 'LIST':
        return ListArgument(name, arg_type, description, state, types)
    elif kind == 'INPUT_OBJECT':
        return InputArgument(name, arg_type, description, state, types)
    elif kind == 'ENUM':
        return EnumArgument(name, arg_type, description, state, types)
    else:
        return ScalarArgument(name, arg_type, description, state, types)


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
        self._all_fields = None

    def make_compact(self):
        if self._all_fields is None:
            return

        self._fields = [
            field
            for field in self._all_fields
            if field.is_selected()
        ]

        for field in self._fields:
            field.make_compact()

        self.set_next_and_prev()

    def make_not_compact(self):
        if self._all_fields is None:
            return

        self._fields = self._all_fields

        for field in self._fields:
            field.make_not_compact()

        self.set_next_and_prev()

    def set_next_and_prev(self):
        if len(self._fields) > 1:
            for i in range(1, len(self._fields)):
                self._fields[i - 1].next = self._fields[i]
                self._fields[i].prev = self._fields[i - 1]

        if len(self._fields) > 0:
            self._fields[0].prev = None
            self._fields[-1].next = None

    def fields(self):
        if self._all_fields is None:
            self._all_fields = [
                build_argument(argument, self._types, self._state)
                for argument in self._arguments_info
            ] + [
                build_field(field, self._types, self._state)
                for field in self._fields_info
            ]

            for field in self._all_fields:
                field.parent = self.parent

            self._fields = self._all_fields
            self.set_next_and_prev()

        return self._fields

    def __iter__(self):
        return ObjectFieldsIterator(self.fields())

    def __len__(self):
        return len(self.fields())

    def index(self, item):
        return self.fields().index(item)

    def __getitem__(self, key):
        return self.fields()[key]


class MoveSelectedState:

    def __init__(self):
        self.new_cursor = None
        self.is_cursor_seen = False


class Search:

    def __init__(self):
        self._value = ''
        self._pos = 0
        self._match_index = 1
        self._matches = []

    def selected_node(self):
        if self._matches:
            return self._matches[self._match_index - 1]
        else:
            return None

    def match(self, text):
        if self._value:
            return text.lower().find(self._value.lower())
        else:
            return -1

    def is_match(self, text):
        return self.match(text) != -1

    def is_cursor(self, node):
        return node is self._matches[self._match_index - 1]

    def draw(self, stdscr, y, x, text, node):
        addstr(stdscr, y, x, text)

        if not self._matches:
            return

        index = self.match(text)

        if index != -1:
            if self.is_cursor(node):
                color = curses.color_pair(6)
            else:
                color = curses.color_pair(5)

            addstr(stdscr,
                   y,
                   x + index,
                   text[index:index + len(self._value)],
                   color)

    def show(self):
        self._match()

    def hide(self):
        self.reset()

    def reset(self):
        self._value = ''
        self._pos = 0
        self._match_index = 1
        self._matches = []

    def key(self, key):
        self._value, self._pos = edit(self._value,
                                      self._pos,
                                      KEY_BINDINGS.get(key, key))
        self._match()

    def key_up(self):
        if len(self._matches) > 0:
            self._match_index -= 1

            if self._match_index < 1:
                self._match_index = len(self._matches)

    def key_down(self):
        if len(self._matches) > 0:
            self._match_index += 1

            if self._match_index > len(self._matches):
                self._match_index = 1

    def info(self):
        return (self._value, self._pos, self._match_index, len(self._matches))

    def _match(self):
        if self._value:
            # Search for all matching fields.
            pass
        else:
            self._matches = []


class Tree:

    def __init__(self, root, state):
        self._root = root
        self._state = state
        self._cursor = root.fields[0]
        self._search = Search()
        self._state.search = self._search

    def cursor_type(self):
        if self._cursor is None:
            return ''

        return self._cursor.type

    def cursor_description(self):
        if self._cursor is None:
            return None

        return self._cursor.description

    def draw(self, stdscr, y, x):
        cursor = Cursor()
        cursor.node = self._cursor

        return self._root.draw(stdscr, y, x, cursor), cursor

    def _search_update(self):
        matches = []

        if len(self._root.fields) > 0:
            self._find_matches(self._root.fields[0], matches)

        self._search._match_index = 1
        self._search._matches = matches

    def search_show(self):
        self._search.show()
        self._search_update()

    def _update_cursor(self):
        node = self._search.selected_node()

        if node is not None:
            self._cursor = node

    def _find_matches(self, node, matches):
        if node.is_match():
            matches.append(node)

        if node.child is not None:
            self._find_matches(node.child, matches)

        if node.next is not None:
            self._find_matches(node.next, matches)

    def search_hide(self):
        self._search.hide()

    def search_reset(self):
        self._search.reset()

    def search_key(self, key):
        self._search.key(key)
        self._search_update()
        self._update_cursor()

    def search_key_up(self):
        self._search.key_up()
        self._update_cursor()

    def search_key_down(self):
        self._search.key_down()
        self._update_cursor()

    def search_info(self):
        return self._search.info()

    def key_up(self):
        if self._cursor is None:
            return

        if self._cursor.prev is not None:
            self._cursor = self._find_last(self._cursor.prev)
        elif self._cursor.parent is not None:
            self._cursor = self._cursor.parent

    def key_down(self):
        if self._cursor is None:
            return

        if self._cursor.child is not None:
            self._cursor = self._cursor.child
        elif self._cursor.next is not None:
            self._cursor = self._cursor.next
        elif self._cursor.parent is not None:
            cursor = self._find_first_below(self._cursor)

            if cursor is not None:
                self._cursor = cursor

    def key_left(self):
        if self._cursor is None:
            return

        if self._cursor.key_left():
            return

        if self._cursor.parent is not None:
            self._cursor = self._cursor.parent

    def key_right(self):
        if self._cursor is None:
            return

        if self._cursor.key_right():
            return

        if self._cursor.child is not None:
            self._cursor = self._cursor.child

    def select(self):
        if self._cursor is None:
            return

        self._cursor.select()

    def key(self, key):
        if self._cursor is None:
            return False

        done = self._cursor.key(key)

        if isinstance(self._cursor, ListItem):
            if self._cursor.removed:
                self._cursor = self._cursor.next

        return done

    def query(self):
        return self._root.query_root(self._cursor)

    def toggle_compact(self):
        self._state.compact = not self._state.compact

        if self._state.compact:
            self._move_cursor_to_selected_node_or_none()
            self._root.make_compact()
        else:
            self._root.make_not_compact()

            if self._cursor is None:
                self._cursor = self._root.fields[0]

    def go_to_begin(self):
        if self._cursor is None:
            return

        self._cursor = self._root.fields[0]

    def go_to_end(self):
        if self._cursor is None:
            return

        self._cursor = self._find_last(self._root.fields[-1])

    def _move_cursor_to_selected_node_or_none(self):
        state = MoveSelectedState()

        if self._move_cursor_to_selected_node_or_none_level(self._root.fields[0],
                                                            state):
            self._cursor = state.new_cursor
        else:
            self._cursor = None

    def _move_cursor_to_selected_node_or_none_level(self, node, state):
        if node is self._cursor:
            state.is_cursor_seen = True

        if node.is_selected():
            state.new_cursor = node

        if state.new_cursor is not None and state.is_cursor_seen:
            return True

        if node.child is not None:
            if self._move_cursor_to_selected_node_or_none_level(node.child, state):
                return True

        while node.next is not None:
            if self._move_cursor_to_selected_node_or_none_level(node.next, state):
                return True

            node = node.next

        return False

    def _find_first_below(self, node):
        if node.parent is not None:
            if node.parent.next is not None:
                return node.parent.next
            else:
                return self._find_first_below(node.parent)
        else:
            return None

    def _find_last(self, node):
        if node.child is not None:
            node = node.child

            while node.next is not None:
                node = node.next

            return self._find_last(node)
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
                  state,
                  len(query_fields),
                  True)
    tree.fields[0].cursor = True

    return Tree(tree, state)
