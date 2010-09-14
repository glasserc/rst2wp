import docutils.parsers.rst.directives
from docutils import core, io, nodes, utils
from docutils.parsers.rst import roles, directives, languages
from docutils.parsers.rst import Directive
from config import IMAGES_LOCATION
import magic  # needed to guess file types


class UploadDirective(Directive):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'uploaded_form': directives.unchanged,
        }

    # def __init__(self, *args, **kwargs):
    #     print "Got {args}, {kwargs}".format(args=args, kwargs=kwargs)
    #     Directive.__init__(self, *args, **kwargs)

    def run(self):
        # FIXME: URL?
        filename = self.arguments[0]
        type = self.guess_type(filename)
        new_url = self.options.get('uploaded_form')
        if not new_url:
            new_url = self.upload_file(filename)

            document = self.state_machine.document
            app = document.settings.application
            app.save_info(document, 'upload '+ filename, 'uploaded_form', new_url, IMAGES_LOCATION, image=filename,
                          type='upload')

        node = nodes.paragraph()
        node += nodes.Text("[uploaded file {0} goes here]".format(self.arguments[0]))
        return [node]

    def upload_file(self, filename):
        return "FOO"
        self.wp = self.state_machine.document.settings.wordpress_instance
        return self.wp.upload_file(filename)

    def guess_type(self, filename):
        m = magic.open(magic.MAGIC_NONE)
        m.load()
        type = m.file(filename)
        m.close()
        return type

directives.register_directive('upload', UploadDirective)
