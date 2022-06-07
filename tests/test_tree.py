import unittest

from graphql import build_schema
from graphql import introspection_from_schema

from gqt.tree import load_tree_from_schema


def load_tree(schema):
    return load_tree_from_schema(introspection_from_schema(build_schema(schema)))


class TreeTest(unittest.TestCase):

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
        tree.key_up()
        tree.key_down()
        tree.key_right()
        self.assertEqual(tree.cursor_type(), 'Activity')
        tree.key_down()
        self.assertEqual(tree.cursor_type(), 'String')
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
        self.assertEqual(tree.cursor_type(), 'String')

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
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:"ABC",d:null) {d}}')
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:"ABC") {d}}')
        tree.key_up()
        tree.key_up()
        tree.select()
        self.assertEqual(tree.query(), 'query Query {a(b:$ABC) {d}}')

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

    def test_input_argument(self):
        with self.assertRaises(SystemExit):
            schema = ('type Query {'
                      '  info(config: ConfigInput): Info'
                      '}'
                      'type Info {'
                      '  size: Int!'
                      '}'
                      'input ConfigInput {'
                      '  unit: String!'
                      '  width: Int'
                      '}')
            tree = load_tree(schema)
            tree.key_right()
            tree.key_down()
            # Expand config argument.
            tree.select()
            tree.key_down()
            tree.select()
            tree.key('\t')
            tree.key('m')
            tree.key('e')
            tree.key('t')
            tree.key('r')
            tree.key('i')
            tree.key('c')
            tree.key_down()
            tree.key_down()
            tree.select()
            self.assertEqual(tree.query(),
                             'query Query {info(config: {unit: "metric"}) {size}}')
            self.assertEqual(tree.cursor_type(), 'todo')
