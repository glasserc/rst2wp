# Tests for my freaky custom image directive
import re
import os
import Image
import xml.etree.cElementTree
import mock
import wordpresslib
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # and hope for the best

from docutils import core

import nodes
import my_image
import rst2wp

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

    def mock_run(self, text):
        application = mock.Mock(rst2wp.Rst2Wp)
        application.filename = '/home/ethan/some/directory/test.rst'
        application.config.has_option.return_value = True
        application.config.getboolean.side_effect = lambda section, key: key == 'save_uploads'
        application.has_directive_info = lambda directive, url, key: directive_uris.get(directive, {}).get(url+'.'+key)
        application.get_directive_info = lambda directive, url, key: directive_uris[directive][url+'.'+key]

        directive_uris = {'image': {}}
        output = core.publish_parts(source=text, writer_name='html4css1',
                                    settings_overrides = {'bibliographic_fields': {},
                                                          'application': application,
                                                          'directive_uris': directive_uris})
        return {'output': output['whole'], 'directive_uris': directive_uris,
                'application': application}

    @mock.patch('os.path.exists')
    @mock.patch('os.mkdir')
    @mock.patch('urllib.urlretrieve')
    def test_option_store(self, os_path_exists, os_mkdir, urlretrieve):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :uploaded: http://foo/on/you
   :uploaded-rot90: http://foo-90/on/you"""

        output = self.mock_run(text)
        directive_uris = output['directive_uris']
        html = output['output']


        self.assertEqual(directive_uris['image']['/tmp/foo.jpg.uploaded'], 'http://foo/on/you')
        self.assertEqual(directive_uris['image']['/tmp/foo.jpg.uploaded-rot90'], 'http://foo-90/on/you')

        images = self.find_images(html)
        self.assertEqual(len(images), 1)
        self.match_image(images[0], {'reference': None, 'src': 'http://foo/on/you'})
