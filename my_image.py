## MyImageDirective: a replacement for the Image directive that
## insinuates transforms when necessary.
import docutils.parsers.rst.directives.images
from docutils import core, io, nodes, utils
from docutils.parsers.rst import roles, directives, languages

from config import POSTS_LOCATION, IMAGES_LOCATION, TEMP_DIRECTORY

from my_transforms import DownloadImageTransform, ScaleImageTransform
import os.path

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
            try: os.mkdir(dir)
            except OSError, e:
                # Probably "file exists"
                if e.errno != 17: raise

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
        uri = directives.uri(self.arguments[0])
        self.document = self.state_machine.document
        self.current_form = ''
        self.current_uri = uri
        self.current_filename = self.download_image(self.current_uri)
        self.process_parameters()

        self.run_rotate()
        self.run_scale()
        self.upload()
        return directives.images.Image.run(self)

    def process_parameters(self):
        '''Store all the uploaded forms for this directive with canonical names in document.settings'''
        # FIXME: Canonicalization TBD
        for key in self.options:
            if key.startswith('form-') or key == 'saved_as' or key.startswith('uploaded'):
                self.document.settings.directive_uris['image'][self.current_uri + '.' + key] = self.options[key]

    def run_rotate(self):
        pass

    def run_scale(self):
        pass

    def upload(self):
        pass

    def later():
        #print 'Handling image directive:', uri, self.options
        # directives.images.Image.run eats target, so we store it here
        if 'target' in self.options:
            self.options['orig_target'] = self.options['target']

        # Store the "real" URI for this image -- the argument given in the file.
        self.options['orig_uri'] = uri
        app = document.settings.application

        # Insert transform for DownloadImageTransform if needed -- or use saved_as
        result_nodes = self.change_uri(document, app, uri)

        # Insert transform for scaling
        self.handle_scaling(document, app, result_nodes)

        return result_nodes

    def change_uri(self, document, app, uri):
        if 'saved_as' in self.options or app.has_directive_info(document, 'image', uri, 'saved_as'):
            document.settings.used_images[uri] = True
            if 'saved_as' in self.options:
                real_uri = self.options['saved_as']
            elif app.has_directive_info(document, 'image', uri, 'saved_as'):
                real_uri = app.get_directive_info(document, 'image', uri, 'saved_as')
            print "Using saved location for image:", real_uri

            self.arguments[0] = real_uri
            result_nodes = directives.images.Image.run(self)

        else:
            # Call the super here to update options, etc.
            result_nodes = directives.images.Image.run(self)
            self.insert_pending(document, result_nodes, DownloadImageTransform)

        return result_nodes

    def insert_pending(self, document, result_nodes, pending_class):
        """Insert a pending"""
        pending = nodes.pending(pending_class, rawsource=self.block_text)
        pending.details.update(self.options)
        document.note_pending(pending)

        # This could be any inline element, but we use the image we'd
        # normally have to look coherent.
        last_node = result_nodes[-1]
        if isinstance(last_node, nodes.reference):
            # This happens when there's a :target:
            last_node = last_node.children[0]

        # Embed the pending in the image node
        last_node += pending
        # print("Adding pending of {pending_class}, {pending_id} to node {id}: {node}".format(
        #         pending_class=pending_class, pending_id=id(pending), id=id(last_node), node=last_node))

    def handle_scaling(self, document, app, nodes):
        """Handle scaling an image by inserting a ScaleImageTransform, if necessary."""
        if 'scale' in self.options:
            # FIXME: this is just a sanity check for now because scale replaces target
            # if 'orig_target' in self.options:
            #     raise ValueError("Cannot have both scale and target on image {uri}".format(
            #             uri=directives.uri(self.arguments[0])))
            self.insert_pending(document, nodes, ScaleImageTransform)

directives.register_directive('image', MyImageDirective)
