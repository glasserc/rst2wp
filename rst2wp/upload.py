import os
import mimetypes
import docutils.parsers.rst.directives
from docutils import core, io, nodes
from docutils.parsers.rst import roles, directives, languages
from config import IMAGES_LOCATION
import magic  # needed to guess file types
from directive import DownloadDirective

import utils

class UploadDirective(DownloadDirective):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'uploaded': directives.unchanged,
        }

    # def __init__(self, *args, **kwargs):
    #     print "Got {args}, {kwargs}".format(args=args, kwargs=kwargs)
    #     Directive.__init__(self, *args, **kwargs)

    def run(self):
        # FIXME: URL?
        uri = self.arguments[0]
        self.document = self.state_machine.document
        filename = self.download_image(uri)
        basename = self.uri_filename(filename)
        type = self.guess_type(filename)
        new_url = self.options.get('uploaded')
        if not new_url:
            new_url = self.upload_file(filename)

            document = self.document
            app = document.settings.application
            if not getattr(app, 'preview', None):
                app.save_directive_info(document, 'upload', uri, 'uploaded', new_url)

        node = nodes.container(classes=['wp-caption', 'alignleft'])
        size = self.file_size(filename)
        type = self.guess_type(filename)

        reference = nodes.reference(refuri=new_url)
        reference += nodes.Text(basename)

        para = nodes.paragraph()
        para.extend([nodes.Text("Uploaded: "), reference,
                     nodes.Text(" ({type}, {size})".format(name=filename, type=type, size=size))])

        node += para

        return [node, nodes.container(classes=['clear'])]

    def upload_file(self, filename):
        if not self.state_machine.document.settings.wordpress_instance: return filename
        print("Uploading {0}".format(filename.encode('utf-8')))
        self.wp = self.state_machine.document.settings.wordpress_instance
        return self.wp.upload_file(filename)

    def file_size(self, filename):
        return utils.approximate_size(os.stat(filename).st_size)

    def guess_type(self, filename):
        m = magic.open(magic.MAGIC_NONE)
        m.load()
        type = m.file(filename.encode('utf-8'))
        m.close()
        #print filename, type
        return type

directives.register_directive('upload', UploadDirective)

# WordPress uses mimetypes.guess_type to guess the MIME type
# for a file without looking at it or using file(1) or
# anything. For ReStructuredText files on my machine, this
# breaks. Provide it for this one special case.
mimetypes.add_type('text/plain', '.rst')
