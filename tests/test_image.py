# Tests for my freaky custom image directive
import os
import nodes
import my_image
import mock
import wordpresslib
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # and hope for the best

from docutils import core

class TestImage(unittest.TestCase):
    @mock.patch('os.path.exists')
    @mock.patch('os.mkdir')
    @mock.patch('urllib.urlretrieve')
    def test_option_store(self, os_path_exists, os_mkdir, urlretrieve):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :uploaded: http://foo/on/you
   :uploaded-rot90: http://foo-90/on/you"""

        directive_uris = {'image': {}}
        application = mock.Mock()
        application.filename = '/home/ethan/some/directory/test.rst'
        application.config.has_option.return_value = True
        application.config.getboolean.side_effect = lambda section, key: key == 'save_uploads'

        output = core.publish_parts(source=text,
                                    settings_overrides = {'bibliographic_fields': {},
                                                          'application': application,
                                                          'directive_uris': directive_uris})

        self.assertEqual(directive_uris['image']['/tmp/foo.jpg.uploaded'], 'http://foo/on/you')
        self.assertEqual(directive_uris['image']['/tmp/foo.jpg.uploaded-rot90'], 'http://foo-90/on/you')
