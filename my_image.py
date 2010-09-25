## MyImageDirective: a replacement for the Image directive that
## insinuates transforms when necessary.
import urllib
import docutils.parsers.rst.directives.images
from docutils import core, io, nodes, utils
from docutils.parsers.rst import roles, directives, languages

from config import POSTS_LOCATION, IMAGES_LOCATION, TEMP_DIRECTORY

import os.path

import Image

# Arguments starting with form-* are all OK.
# Simple dictionary that accepts all those options.
class WildDict(dict):
    def __missing__(self, item):
        if item.startswith('form-'): return directives.unchanged
        if item.startswith('uploaded-'): return directives.unchanged
        raise KeyError

# So here's the new plan vis-a-vis images.
#
# Invariant: each image directive OBJECT has a current_form,
# current_filename, and current_url attribute, which represents the
# latest, i.e. most-transformed version of the image.
#
# The image directive IN TEXT has a bunch of uploaded-{current_form}:
# {current_url} mappings.
#
# current_form starts as "". Uploading this should create an uploaded:
# {saved_as} sort of mapping.
#
# Every image transformation that happens should update current_form,
# current_filename, and current_url. Some sample current_forms:
# 'rot90', 'rot90-scale0.25'.
#
# We generate every image corresponding to the version of current_filename,
# since it might be used by the next transformation. We only upload if
# there is not already directive_info for the current_form.  Thus, if
# we change (in text) the :rotate: from 90 to 180, all the old
# uploaded forms, such as uploaded-rot90, uploaded-rot90-scale0.25,
# uploaded-rot90-scale200x200, etc. will all still work. But, the
# rotate transformation will create a new current form, and scale will
# work off of that.
#
# At the end, we call directives.image.Image on whatever's left.
#
# Backwards compatibility with saved_as and form-* should be kept if possible?
class MyImageDirective(directives.images.Image):
    option_spec = WildDict(directives.images.Image.option_spec)
    option_spec.update({'saved_as': directives.unchanged,
                        'rotate': directives.unchanged,
                        'scale': directives.unchanged,
                        'uploaded': directives.unchanged,
                        'title': directives.unchanged})

    @property
    def save_uploads(self, *args, **kwargs):
        '''Needlessly memoized version of the save_uploads property.'''
        if not hasattr(self, '_save_uploads'):
            app = self.document.settings.application
            self._save_uploads = app.config.has_option('config', 'save_uploads') and \
                app.config.getboolean('config', 'save_uploads') == True
        return self._save_uploads

    def uploads_dir(self):
        '''Directory where things-to-be-uploaded go.

        If save_uploads is True, this is an uploads/ directory in the
        same directory as the post was found. Otherwise, use a temp
        directory.'''
        app = self.document.settings.application
        dir = TEMP_DIRECTORY
        if self.save_uploads:
            dir = os.path.join(os.path.dirname(app.filename), 'uploads')
            if not os.path.exists(dir):
                os.mkdir(dir)

        return dir

    def cleanup_file(self, filename):
        '''Mark file specified by 'filename' as temporary, with a need to be cleaned up.'''
        if not self.save_uploads and filename.startswith(TEMP_DIRECTORY):
            TEMP_FILES.append(filename)

    def download_image(self, uri):
        '''Download the image specified by uri to an appropriate uploads_dir. Return the filename of the local image.'''
        target_filename = self.uri_filename(uri)
        dir = self.uploads_dir()

        filename = os.path.join(dir, target_filename)
        if not os.path.exists(filename):
            print("Downloading {0}".format(uri))
            filename, headers = urllib.urlretrieve(uri, os.path.join(dir, target_filename))

        self.cleanup_file(filename)
        return filename

    def uri_filename(self, uri):
        # FIXME: this might not work on non-Unix -- but who cares?
        target_filename = os.path.split(uri)[1]
        if '?' in target_filename:
            target_filename = target_filename[:target_filename.index('?')]
        if '.' not in target_filename:
            target_filename = raw_input("Image specified by %s doesn't have a filename.\nWhat would you like this image to be named?\n> "%(uri,))

        return target_filename

    def run(self):
        self.uri = directives.uri(self.arguments[0])
        self.document = self.state_machine.document
        self.process_parameters()

        self.compute_image()

        return directives.images.Image.run(self)

    def form_to_attribute_name(self, desired_form):
        if desired_form:
            return 'uploaded-'+desired_form
        return'uploaded'

    def compute_image(self):
        desired_form = ''
        if 'rotate' in self.options:
            desired_form = self.update_form(desired_form, 'rot{0}'.format(self.options['rotate']))

        if 'scale' in self.options:
            desired_form = self.update_form(desired_form, 'scale{0}'.format(self.options['scale']))

        desired_form = self.form_to_attribute_name(desired_form)

        if self.document.settings.application.has_directive_info(self.document, 'image', self.uri, desired_form):
            self.arguments[0] = self.document.settings.application.get_directive_info(self.document, 'image', self.uri, desired_form)
            if 'scale' in self.options and 'target' not in self.options:
                # Link to non-scaled form.
                # This could get super-complicated. We assume for
                # simplicity here that the rotated version must exist
                # if the rotated-and-scaled version exists.
                non_scaled_form = ''
                if 'rotate' in self.options:
                    non_scaled_form = 'rot{0}'.format(self.options['rotate'])

                non_scaled_form = self.form_to_attribute_name(non_scaled_form)
                self.options['target'] = \
                    self.document.settings.application.get_directive_info(self.document, 'image', self.uri, non_scaled_form)
            return

        self.current_form = ''
        self.current_uri = None
        self.current_filename = self.download_image(self.uri)

        if 'rotate' in self.options:
            self.run_rotate()

        if 'scale' in self.options:
            self.run_scale()
        self.upload()

    def process_parameters(self):
        '''Store all the uploaded forms for this directive with canonical names in document.settings'''
        # FIXME: Canonicalization TBD
        for key in self.options:
            if key.startswith('form-') or key == 'saved_as' or key.startswith('uploaded'):
                self.document.settings.directive_uris['image'][self.uri + '.' + key] = self.options[key]

    def update_form(self, form, suffix):
        if form:
            return '-'.join([form, suffix])
        return suffix

    def filename_insert_before_extension(self, filename, suffix):
        head, ext = os.path.splitext(filename)
        new_filename = "{head}-{suffix}{ext}".format(head=head, suffix=suffix, ext=ext)
        return new_filename

    def run_rotate(self):
        # N.B. doesn't upload previous version, since we don't want
        # people to see it.
        degrees = self.options['rotate']
        suffix = 'rot{degrees}'.format(degrees=degrees)

        new_filename = self.filename_insert_before_extension(self.current_filename, suffix)
        degrees = float(degrees)

        image = Image.open(self.current_filename)
        image = image.rotate(degrees)
        image.save(new_filename)

        self.current_filename = new_filename
        self.current_form = self.update_form(self.current_form, suffix)

    def run_scale(self):
        # Remove option for 'scale' because html4css1 writer tries to
        # do its own scaling on top of ours if it's present.
        scale = self.options.pop('scale')

        suffix = 'scale{scale}'.format(scale=scale)
        new_filename = self.filename_insert_before_extension(self.current_filename, suffix)

        self.upload()
        self.options['target'] = self.current_uri

        image = Image.open(self.current_filename)
        if scale:
            dimensions = factor = None
            try:
                factor = float(scale)
                dimensions = image.size
                dimensions = int(dimensions[0]*factor), int(dimensions[1]*factor)
            except ValueError, e:
                dimensions = scale.split('x')
                dimensions = int(dimensions[0]), int(dimensions[1])

        image.thumbnail(dimensions, Image.ANTIALIAS)
        image.save(new_filename)

        self.current_filename = new_filename
        self.current_form = self.update_form(self.current_form, suffix)

    def upload(self):
        key = self.form_to_attribute_name(self.current_form)
        if not self.document.settings.application.has_directive_info(self.document, 'image', self.uri, key):
            if self.document.settings.application.preview:
                self.arguments[0] = self.current_uri = os.path.join(os.getcwd(), self.current_filename)
                return
            else:
                uploaded = self.document.settings.wordpress_instance.upload_file(self.current_filename)
                self.document.settings.application.save_directive_info(self.document, 'image', self.uri, key, uploaded)

        self.arguments[0] = self.current_uri = \
            self.document.settings.application.get_directive_info(self.document, 'image', self.uri, key)

directives.register_directive('image', MyImageDirective)
