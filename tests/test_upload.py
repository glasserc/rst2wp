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

    def mock_run(self):
        def fake_os_stat(filename):
            m = mock.Mock()
            m.st_size = 1337
            return m

        with mock.patch('os.path.exists') as os_path_exists:
            with mock.patch('os.stat') as os_stat:
                with mock.patch('magic.open') as magic_open:
                    os_path_exists.side_effect = lambda filename: filename.endswith('file.odf')
                    os_stat.side_effect = fake_os_stat
                    magic_open().file.side_effect = 'text/plain'
                    return self.up.run()

    def test_upload(self):
        self.create_directive('/path/to/file.odf')
        self.assertEqual(self.up.arguments, ['/path/to/file.odf'])

        output = self.mock_run()

        assert self.state_machine.document.settings.wordpress_instance.upload_file.called
        self.assertEqual(self.state_machine.document.settings.wordpress_instance.upload_file.call_args_list,
                         [mock.call('/tmp/file.odf')])

    def test_no_upload(self):
        self.create_directive('/path/to/file.odf')
        self.up.options['uploaded'] = 'http://example.com/already/exists'

        output = self.mock_run()
        self.assertFalse(self.state_machine.document.settings.wordpress_instance.upload_file.called)
