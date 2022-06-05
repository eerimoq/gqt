import unittest

from graphql import build_schema
from graphql import introspection_from_schema

from gqt.tree import load_tree_from_schema


class TreeTest(unittest.TestCase):

    def test_basic(self):
        schema = ('type Query {'
                  '  activity: Activity'
                  '}'
                  ''
                  'type Activity {'
                  '  date: String!'
                  '  kind: String!'
                  '  message: String!'
                  '}')
        tree = load_tree_from_schema(introspection_from_schema(build_schema(schema)))
        tree.key_up()
        tree.key_down()
        tree.key_right()
        tree.key_down()
        # Select date.
        tree.select()
        tree.key_down()
        tree.key_down()
        # Select message.
        tree.select()
        tree.key_down()
        tree.select()
        tree.select()
        self.assertEqual(tree.query(), '{activity {date message}}')
