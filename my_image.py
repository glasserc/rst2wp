## MyImageDirective: a replacement for the Image directive that
## insinuates transforms when necessary.
import docutils.parsers.rst.directives.images
from docutils.parsers.rst import roles, directives, languages

from my_transforms import DownloadImageTransform, ScaleImageTransform

# Arguments starting with form-* are all OK.
# Simple dictionary that accepts all those options.
class WildDict(dict):
    def __missing__(self, item):
        if item.startswith('form-'): return directives.unchanged
        raise KeyError

class MyImageDirective(directives.images.Image):
    option_spec = WildDict(directives.images.Image.option_spec)
    option_spec.update({'saved_as': directives.unchanged,
                        'scale': directives.unchanged,
                        'title': directives.unchanged})

    def run(self):
        uri = directives.uri(self.arguments[0])
        #print 'Handling image directive:', uri, self.options
        # directives.images.Image.run eats target, so we store it here
        if 'target' in self.options:
            self.options['orig_target'] = self.options['target']

        # Store the "real" URI for this image -- the argument given in the file.
        self.options['orig_uri'] = uri
        document = self.state_machine.document
        app = document.settings.application

        # Store all the saved forms of this image in document.settings.
g        for key in self.options:
            if key.startswith('form-') or key == 'saved_as':
                document.settings.image_uris['image ' + uri + '.' + key] = self.options[key]

        # Insert transform for DownloadImageTransform if needed -- or use saved_as
        result_nodes = self.change_uri(document, app, uri)

        # Insert transform for scaling
        self.handle_scaling(document, app, result_nodes)

        return result_nodes

    def change_uri(self, document, app, uri):
        if 'saved_as' in self.options or app.has_info(document, 'image '+uri, 'new uri', location=IMAGES_LOCATION) \
                or app.has_info(document, 'image '+uri, 'saved_as', location=IMAGES_LOCATION):
            document.settings.used_images[uri] = True
            if 'saved_as' in self.options:
                real_uri = self.options['saved_as']
            elif app.has_info(document, 'image '+uri, 'saved_as', location=IMAGES_LOCATION):
                real_uri = app.get_info(document, 'image ' + uri, 'saved_as', location=IMAGES_LOCATION)
            else:
                real_uri = app.get_info(document, 'image ' + uri, 'new uri', location=IMAGES_LOCATION)
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
            last_node = last_node.children[0]

        # Embed the pending in the image node
        last_node += pending

    def handle_scaling(self, document, app, nodes):
        """Handle scaling an image by inserting a ScaleImageTransform, if necessary."""
        if 'scale' in self.options:
            # FIXME: this is just a sanity check for now because scale replaces target
            # if 'orig_target' in self.options:
            #     raise ValueError("Cannot have both scale and target on image {uri}".format(
            #             uri=directives.uri(self.arguments[0])))
            self.insert_pending(document, nodes, ScaleImageTransform)

directives.register_directive('image', MyImageDirective)
