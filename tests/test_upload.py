from rst2wp import upload
from unittest import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # and hope for the best

class TestUpload(unittest.TestCase):
    def create_directive(self, filename, **kwargs):
        self.state_machine = mock.Mock()
        self.up = upload.UploadDirective('upload', [filename], {}, None, 'lineno', 'content_offset', '.. upload::', 'state', self.state_machine)

    def test_upload(self):
        self.create_directive('/path/to/file.odf')
        self.assertEqual(self.up.arguments, ['/path/to/file.odf'])

        output = self.up.run()

        assert self.state_machine.document.settings.wordpress_instance.upload_file.called
        self.assertEqual(self.state_machine.document.settings.wordpress_instance.upload_file.call_args_list,
                         [(('/path/to/file.odf',), {})])

    def test_no_upload(self):
        self.create_directive('/path/to/file.odf')
        self.up.options['uploaded'] = 'http://example.com/already/exists'

        output = self.up.run()
        self.assertFalse(self.state_machine.document.settings.wordpress_instance.upload_file.called)
