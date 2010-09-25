# Tests for my freaky custom image directive
import re
import os
import xml.etree.cElementTree
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
    def find_images(self, output):
        images = []
        img_re = re.compile('(<a href="([^>]+)">)?<img[^>]+>(</a>)?')
        for img in img_re.finditer(output):
            elem = xml.etree.cElementTree.XML(img.group(0))
            data = {'reference': None}
            if elem.tag == 'a':
                data['reference'] = elem.attrib['href']
                elem = elem[0]

            data['src'] = elem.attrib['src']
            data['alt'] = elem.attrib.get('alt')
            data['title'] = elem.attrib.get('title')

            images.append(data)

        return images

    def match_image(self, image, spec):
        for x in spec:
            if image[x] != spec[x]:
                raise AssertionError, "Image {0} did not match spec {1}".format(image, spec)

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

        output = core.publish_parts(source=text, writer_name='html4css1',
                                    settings_overrides = {'bibliographic_fields': {},
                                                          'application': application,
                                                          'directive_uris': directive_uris})

        self.assertEqual(directive_uris['image']['/tmp/foo.jpg.uploaded'], 'http://foo/on/you')
        self.assertEqual(directive_uris['image']['/tmp/foo.jpg.uploaded-rot90'], 'http://foo-90/on/you')

        images = self.find_images(output['whole'])
        self.assertEqual(len(images), 1)
        self.match_image(images[0], {'reference': None, 'src': '/tmp/foo.jpg'})
