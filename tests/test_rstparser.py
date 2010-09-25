import nodes
import mock
import wordpresslib
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # and hope for the best

from docutils import core

class TestNodes(unittest.TestCase):
    def test_field_loader(self):
        text = """
:title: Hello
:foo: - test1
      - test2
      - test3
:category: default_category
:tags: - tag1
       - tag2

This is a test."""

        fields = {}

        output = core.publish_parts(source=text,
                                    settings_overrides = {'fields': fields})

        self.assertEqual(fields['title'], 'Hello')
        self.assertEqual(fields['foo'], ['test1', 'test2', 'test3'])
        self.assertEqual(fields['tags'], ['tag1', 'tag2'])
        self.assertEqual(fields['categories'], ['default_category'])

    @mock.patch('nodes.raw_input')
    def test_validity(self, raw_input):
        text = '''
:tags: - tag1
       - tag2

This is a test.'''

        fields = {}
        wordpress_instance = mock.Mock(wordpresslib.WordPressClient)
        wordpress_instance.has_tag.side_effect = lambda tag: tag == 'tag1'

        output = core.publish_parts(source=text,
                                    settings_overrides = {
                'fields': fields,
                'wordpress_instance': wordpress_instance
                })

        wordpress_instance.has_tag.asssert_called_with("tag1")
        wordpress_instance.has_tag.asssert_called_with("tag2")
        assert raw_input.called
