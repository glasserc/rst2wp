import upload
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # and hope for the best

class TestUpload(unittest.TestCase):
    def create_directive(self, filename, **kwargs):
        self.state_machine = mock.Mock()
        self.up = upload.UploadDirective('upload', [filename], {}, None, 'lineno', 'content_offset', '.. upload::', 'state', self.state_machine)

    def test_upload(self):
        self.create_directive('/path/to/file')
        print self.up.arguments
