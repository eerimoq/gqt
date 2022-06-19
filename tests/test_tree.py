import unittest
from unittest.mock import patch

from graphql import build_schema
from graphql import introspection_from_schema

from gqt.tree import load_tree_from_schema


def load_tree(schema):
    return load_tree_from_schema(introspection_from_schema(build_schema(schema)))


class Stdscr:

    def __init__(self, y_max, x_max):
        self.y_max = y_max
        self.x_max = x_max
        self.screen = [
            [' ' for _ in range(x_max)]
            for _ in range(y_max)
        ]

    def addstr(self, y, x, text, _attrs=None):
        if not 0 <= y < self.y_max:
            return

        if x > self.x_max:
            return

        text = text[:self.x_max - x]
        self.screen[y][x:x + len(text)] = list(ch for ch in text)

    def getmaxyx(self):
        return self.y_max, self.x_max

    def render(self):
        return '\n'.join(''.join(line).rstrip() for line in self.screen).rstrip()


class TreeTest(unittest.TestCase):

    def assertDraw(self, tree, expected):
        stdscr = Stdscr(40, 20)

        with patch('curses.color_pair'):
            _, cursor = tree.draw(stdscr, 0, 0)

        stdscr.addstr(cursor.y, cursor.x, 'X')
        self.assertEqual(stdscr.render(), expected)

    def test_basic(self):
        schema = ('type Query {'
                  '  activity: Activity'
                  '}'
                  'type Activity {'
                  '  date: String!'
                  '  kind: String!'
                  '  message: String!'
                  '}')
        tree = load_tree(schema)
        self.assertEqual(tree.cursor_type(), 'Activity')
        self.assertDraw(tree, 'X activity')
        tree.key_up()
        tree.key_down()
        tree.key_right()
        self.assertEqual(tree.cursor_type(), 'Activity')
        self.assertDraw(tree,
                        'X activity\n'
                        '  □ date\n'
                        '  □ kind\n'
                        '  □ message')
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'String!')
        # Select date.
        tree.select()
        tree.key_down()
        tree.key_down()
        # Select message.
        tree.select()
        tree.key_down()
        tree.select()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {activity {date message}}')
        self.assertEqual(tree.cursor_type(), 'String!')
        self.assertDraw(tree,
                        '▼ activity\n'
                        '  ■ date\n'
                        '  □ kind\n'
                        '  X message')

    def test_move_up_into_expanded_object(self):
        schema = ('type Query {'
                  '  foo: Foo'
                  '}'
                  'type Foo {'
                  '  bar: Bar'
                  '  fie: String'
                  '}'
                  'type Bar {'
                  '  a: String'
                  '  b: String'
                  '  c: String'
                  '}')
        tree = load_tree(schema)
        # Expand foo.
        tree.key_right()
        tree.key_down()
        # Expand bar.
        tree.key_right()
        tree.key_down()
        tree.key_down()
        tree.key_down()
        tree.key_down()
        # Select fie.
        tree.select()
        tree.key_up()
        # Select c.
        tree.select()
        self.assertEqual(tree.query(), 'query Query {foo {bar {c} fie}}')
        self.assertEqual(tree.cursor_type(), 'String')
        self.assertDraw(tree,
                        '▼ foo\n'
                        '  ▼ bar\n'
                        '    □ a\n'
                        '    □ b\n'
                        '    X c\n'
                        '  ■ fie')

    def test_move_up_through_expanded_objects(self):
        schema = ('type Query {'
                  '  a: String'
                  '  b: Foo'
                  '}'
                  'type Foo {'
                  '  c: Foo'
                  '  d: String'
                  '}')
        tree = load_tree(schema)
        tree.key_down()
        # Expand b.
        tree.key_right()
        tree.key_down()
        tree.key_right()
        tree.key_down()
        tree.key_down()
        # Select d.
        tree.select()
        tree.key_up()
        tree.key_up()
        tree.key_up()
        tree.key_up()
        # Select a.
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a b {c {d}}}')
        self.assertEqual(tree.cursor_type(), 'String')
        self.assertDraw(tree,
                        'X a\n'
                        '▼ b\n'
                        '  ▼ c\n'
                        '    ▶ c\n'
                        '    ■ d\n'
                        '  □ d')

    def test_move_left_collapse_objects(self):
        schema = ('type Query {'
                  '  a: Foo'
                  '  b: String'
                  '}'
                  'type Foo {'
                  '  c: Foo'
                  '  d: String'
                  '}')
        tree = load_tree(schema)
        # Expand.
        tree.key_right()
        tree.key_right()
        tree.key_right()
        tree.key_right()
        tree.key_right()
        tree.key_right()
        tree.key_down()
        # Select d.
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a {c {c {d}}}}')
        self.assertEqual(tree.cursor_type(), 'String')
        # Collapse.
        tree.key_left()
        tree.key_left()
        tree.key_left()
        tree.key_left()
        tree.key_left()
        tree.key_left()
        tree.key_down()
        # Select b.
        tree.select()
        self.assertEqual(tree.query(), 'query Query {b}')
        self.assertEqual(tree.cursor_type(), 'String')

    def test_argument(self):
        schema = ('type Query {'
                  '  a(b: String!, c: Int, d: Int): Foo'
                  '}'
                  'type Foo {'
                  '  d: String'
                  '}')
        tree = load_tree(schema)
        tree.key_right()
        tree.key_down()
        tree.key('\t')
        tree.key('B')
        tree.key_left()
        tree.key('A')
        tree.key_right()
        tree.key('C')
        tree.key_down()
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Int')
        tree.key('\t')
        tree.select()
        tree.key('\t')
        tree.key('1')
        tree.key_down()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:"ABC",d:1) {d}}')
        self.assertEqual(tree.cursor_type(), 'String')
        tree.key_up()
        tree.key('\t')
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:"ABC") {d}}')
        tree.key('v')
        tree.key('\t')
        tree.key('\x7f')

        with self.assertRaises(Exception) as cm:
            tree.query()

        self.assertEqual(str(cm.exception), 'Missing variable name.')
        tree.key('f')
        tree.key('o')
        tree.key('o')
        self.assertEqual(tree.query(),
                         'query Query($foo:Int) {a(b:"ABC",d:$foo) {d}}')

    def test_argument_to_scalar_field(self):
        schema = ('type Query {'
                  '  a(b: String!, c: Int): String'
                  '  b: Foo'
                  '}'
                  'type Foo {'
                  '  f: String'
                  '}')
        tree = load_tree(schema)
        self.assertEqual(tree.cursor_type(), 'String')
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Foo')
        tree.key_up()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:"")}')
        tree.key_down()
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Int')
        tree.select()
        tree.key('\t')
        tree.key('9')
        self.assertEqual(tree.query(), 'query Query {a(b:"",c:9)}')
        tree.key('\t')
        tree.select()
        tree.key_down()
        tree.key_right()
        tree.key_down()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:"") b {f}}')
        tree.key_up()
        tree.key_left()
        tree.key_up()
        tree.key_up()
        tree.key('v')

        with self.assertRaises(Exception) as cm:
            tree.query()

        self.assertEqual(str(cm.exception), 'Missing variable name.')
        tree.key('\t')
        tree.key('v')
        self.assertEqual(tree.query(), 'query Query($v:String!) {a(b:$v)}')

    def test_move_down_at_expanded_object_at_bottom(self):
        schema = ('type Query {'
                  '  a: Foo'
                  '}'
                  'type Foo {'
                  '  b: String'
                  '}')
        tree = load_tree(schema)
        tree.key_right()
        tree.key_down()
        tree.key_down()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a {b}}')
        self.assertEqual(tree.cursor_type(), 'String')

    def test_mutation(self):
        schema = ('type Query {'
                  '  a: String'
                  '}'
                  'type Mutation {'
                  '  b(c: Int!): Info'
                  '}'
                  'type Info {'
                  '  size: Int!'
                  '}')
        tree = load_tree(schema)
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Info')
        tree.key_right()
        tree.key_down()
        tree.key('\t')
        tree.key('5')
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Int!')
        tree.select()
        self.assertEqual(tree.query(), 'mutation Mutation {b(c:5) {size}}')

    def test_recursive_type(self):
        schema = ('type Query {'
                  '  foo: Foo'
                  '}'
                  'type Foo {'
                  '  foo: Foo'
                  '  value: String'
                  '}')
        tree = load_tree(schema)
        # Expand foo.
        tree.key_right()
        tree.key_down()
        tree.key_right()
        tree.key_down()
        # Select value.
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'String')
        tree.select()
        self.assertEqual(tree.query(), 'query Query {foo {foo {value}}}')

    def test_list_argument(self):
        schema = ('type Query {'
                  '  a(b: [String]): String'
                  '  b: String'
                  '}')
        tree = load_tree(schema)
        tree.select()
        tree.key_down()
        self.assertEqual(tree.query(), 'query Query {a}')
        self.assertEqual(tree.cursor_type(), '[String]')
        tree.select()
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'String')
        self.assertEqual(tree.query(), 'query Query {a(b:[])}')
        tree.key_right()
        self.assertEqual(tree.query(), 'query Query {a(b:[null])}')
        tree.key_down()
        tree.select()
        tree.key('\t')
        tree.key('g')
        self.assertEqual(tree.query(), 'query Query {a(b:["g"])}')
        tree.key_down()
        tree.key_right()
        self.assertEqual(tree.query(), 'query Query {a(b:["g", null])}')
        tree.key_down()
        tree.key_down()
        tree.key_down()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:["g", null]) b}')
        tree.key_up()
        tree.key_up()
        tree.key_up()
        tree.key_left()
        self.assertEqual(tree.query(), 'query Query {a(b:["g"]) b}')
        tree.key_up()
        tree.key_up()
        tree.key('\x7f')
        tree.key_right()
        self.assertEqual(tree.query(), 'query Query {a(b:[null]) b}')
        tree.key('\x7f')
        self.assertEqual(tree.query(), 'query Query {a(b:[]) b}')
        tree.key('\x7f')
        self.assertEqual(tree.query(), 'query Query {a(b:[]) b}')
        tree.key_right()
        self.assertEqual(tree.query(), 'query Query {a(b:[null]) b}')

    def test_input_argument(self):
        schema = ('type Query {'
                  '  a(x: Foo): String'
                  '}'
                  'input Foo {'
                  '  y: Bar!'
                  '}'
                  'input Bar {'
                  '  z: String'
                  '}')
        tree = load_tree(schema)
        tree.select()
        tree.key_down()
        self.assertEqual(tree.query(), 'query Query {a}')
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(x:{y:{}})}')
        tree.key_down()
        tree.key_down()
        tree.select()
        tree.key('\t')
        tree.key('B')
        self.assertEqual(tree.query(), 'query Query {a(x:{y:{z:"B"}})}')

    def test_enum_argument(self):
        schema = ('type Query {'
                  '  a(x: Foo): String'
                  '}'
                  'enum Foo {'
                  '  A'
                  '  B'
                  '  C'
                  '}')
        tree = load_tree(schema)
        tree.select()
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Foo')
        tree.select()
        self.assertDraw(tree,
                        '■ a\n'
                        '  X x:  (A, B, C)')

        with self.assertRaises(Exception) as cm:
            tree.query()

        self.assertEqual(str(cm.exception), "Missing enum value.")
        tree.key('\t')
        tree.key('D')

        with self.assertRaises(Exception) as cm:
            tree.query()

        self.assertEqual(str(cm.exception), "Invalid enum value 'D'.")
        tree.key('\x08')
        tree.key('C')
        self.assertEqual(tree.query(), 'query Query {a(x:C)}')
        tree.key('\t')
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a}')
        self.assertDraw(tree,
                        '■ a\n'
                        '  X x: C')

    def test_interface(self):
        schema = ('type Query {'
                  '  a: Foo'
                  '}'
                  'interface Foo {'
                  '  b: String'
                  '}')
        tree = load_tree(schema)
        tree.key_right()
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'String')
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a {b}}')

    def test_union(self):
        schema = ('union SearchResult = Book | Author '
                  'type Book {'
                  '  title: String!'
                  '}'
                  'type Author {'
                  '  name: String!'
                  '}'
                  'type Query {'
                  '  search(contains: String): [SearchResult!]'
                  '}')
        tree = load_tree(schema)
        tree.key_right()
        tree.key_down()
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'Book')
        tree.key_right()
        tree.key_down()
        tree.select()
        self.assertEqual(tree.query(),
                         'query Query {search {__typename ... on Book {title}}}')
        tree.key_down()
        tree.key_right()
        tree.key_down()
        tree.select()
        self.assertEqual(tree.query(),
                         'query Query {search {__typename ... on Book {title} '
                         '... on Author {name}}}')
        tree.key_up()
        tree.key_up()
        tree.key_up()
        tree.key_up()
        tree.select()
        tree.key('\t')
        tree.key_right()
        tree.key('k')
        self.assertEqual(tree.query(),
                         'query Query {search(contains:"k") '
                         '{__typename ... on Book {title} ... on Author {name}}}')
        self.assertDraw(tree,
                        '▼ search\n'
                        '  ■ contains: kX\n'
                        '  ▼ Book\n'
                        '    ■ title\n'
                        '  ▼ Author\n'
                        '    ■ name')
