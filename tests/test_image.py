# Tests for my freaky custom image directive
import re
import os
import xml.etree.cElementTree
import Image
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
        img_re = re.compile('(<a([^>]+)>)?<img[^>]+>(</a>)?')
        for img in img_re.finditer(output):
            print img.group(0)
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

        wp = mock.Mock(wordpresslib.WordPressClient)
        wp.upload_file.side_effect = lambda filename, overwrite=True: "http://wordpress/"+os.path.basename(filename)

        directive_uris = {'image': {}}
        output = core.publish_parts(source=text, writer_name='html4css1',
                                    settings_overrides = {'bibliographic_fields': {},
                                                          'application': application,
                                                          'directive_uris': directive_uris,
                                                          'wordpress_instance': wp})
        return {'output': output['whole'], 'directive_uris': directive_uris,
                'application': application, 'wordpress_instance': wp}

    def test_option_store(self):
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

    def test_option_stored_rot90(self):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :rotate: 90
   :uploaded: http://foo/on/you
   :uploaded-rot90: http://foo-90/on/you"""

        output = self.mock_run(text)
        html = output['output']

        images = self.find_images(html)
        self.assertEqual(len(images), 1)
        self.match_image(images[0], {'reference': None, 'src': 'http://foo-90/on/you'})

    def test_option_stored_scale025(self):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :scale: 0.25
   :uploaded: http://foo/on/you
   :uploaded-scale0.25: http://foo-scale0.25/on/you"""

        output = self.mock_run(text)
        html = output['output']

        images = self.find_images(html)
        self.assertEqual(len(images), 1)
        self.match_image(images[0], {'reference': None, 'src': 'http://foo-scale0.25/on/you'})

    def test_option_stored_rot90_scale025(self):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :rotate: 90
   :scale: 0.25
   :uploaded: http://foo/on/you
   :uploaded-rot90: http://foo-90/on/you
   :uploaded-scale0.25: http://foo-scale0.25/on/you
   :uploaded-scale0.50: http://foo-scale0.25/on/you
   :uploaded-rot90-scale0.25: http://foo-rot90-scale0.25/on/you"""

        output = self.mock_run(text)
        html = output['output']

        images = self.find_images(html)
        self.assertEqual(len(images), 1)
        # FIXME: reference needs to point to uploaded-rot90
        self.match_image(images[0], {'reference': None, 'src': 'http://foo-rot90-scale0.25/on/you'})


    @mock.patch('Image.open')
    @mock.patch('urllib.urlretrieve')
    @mock.patch('os.mkdir')
    @mock.patch('os.path.exists')
    def test_rotate(self, os_path_exists, os_mkdir, urlretrieve, image_open):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :rotate: 90"""

        os_path_exists.side_effect = lambda filename: filename != '/home/ethan/some/directory/uploads/foo.jpg'
        urlretrieve.side_effect = lambda filename, target: (target, [])

        output = self.mock_run(text)
        html = output['output']
        application = output['application']

        #os_path_exists.assert_called_with('/home/ethan/some/directory/uploads')
        assert not os_mkdir.called
        urlretrieve.assert_called_with('/tmp/foo.jpg', '/home/ethan/some/directory/uploads/foo.jpg')
        image_open.assert_called_with('/home/ethan/some/directory/uploads/foo.jpg')
        image_open.return_value.rotate.assert_called_with(90)
        image_open.return_value.rotate.return_value.\
            save.assert_called_with('/home/ethan/some/directory/uploads/foo-rot90.jpg')

        application.save_directive_info.assert_called_with('image', '/tmp/foo.jpg', 'uploaded-rot90',
                                                           'http://wordpress/foo-rot90.jpg')

        images = self.find_images(html)
        self.assertEqual(len(images), 1)
        self.match_image(images[0], {'reference': None, 'src': 'http://wordpress/foo-rot90.jpg'})

    @mock.patch('Image.open')
    @mock.patch('urllib.urlretrieve')
    @mock.patch('os.mkdir')
    @mock.patch('os.path.exists')
    def test_rotate_and_scale(self, os_path_exists, os_mkdir, urlretrieve, image_open):
        text = """
:title: Hello

.. image:: /tmp/foo.jpg
   :scale: 0.25
   :rotate: 90
"""

        os_path_exists.side_effect = lambda filename: not filename.startswith('/home/ethan/some/directory/uploads/foo')
        urlretrieve.side_effect = lambda filename, target: (target, [])

        images = [mock.Mock(), mock.Mock()]
        images[1].size = (4000, 3000)
        images_iter = iter(images)

        image_open.side_effect = lambda filename: images_iter.next()

        output = self.mock_run(text)
        html = output['output']
        application = output['application']

        #os_path_exists.assert_called_with('/home/ethan/some/directory/uploads')
        assert not os_mkdir.called
        urlretrieve.assert_called_with('/tmp/foo.jpg', '/home/ethan/some/directory/uploads/foo.jpg')
        self.assertEqual(image_open.call_args_list, [(('/home/ethan/some/directory/uploads/foo.jpg',), {}),
                                                     (('/home/ethan/some/directory/uploads/foo-rot90.jpg',), {})])
        images[0].rotate.assert_called_with(90)
        images[0].rotate.return_value.\
            save.assert_called_with('/home/ethan/some/directory/uploads/foo-rot90.jpg')

        images[1].thumbnail.assert_called_with((1000, 750), Image.ANTIALIAS)
        images[1].\
            save.assert_called_with('/home/ethan/some/directory/uploads/foo-rot90-scale0.25.jpg')

        self.assertEqual(application.save_directive_info.call_args_list, [
                (('image', '/tmp/foo.jpg', 'uploaded-rot90', 'http://wordpress/foo-rot90.jpg'), {}),
                (('image', '/tmp/foo.jpg', 'uploaded-rot90-scale0.25', 'http://wordpress/foo-rot90-scale0.25.jpg'), {})
        ])

        images = self.find_images(html)
        self.assertEqual(len(images), 1)
        self.match_image(images[0], {
                'reference': 'http://wordpress/foo-rot90.jpg',
                'src': 'http://wordpress/foo-rot90-scale0.25.jpg'
                })
