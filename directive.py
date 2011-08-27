import os.path

import urllib
import urlparse
from docutils.parsers.rst import Directive
from config import POSTS_LOCATION, IMAGES_LOCATION, TEMP_DIRECTORY


class DownloadDirective(Directive):
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
        tuple = urlparse.urlparse(uri)
        path = tuple.path
        target_filename = path.split('/')[-1]
        if '.' not in target_filename:
            target_filename = raw_input("Image specified by %s doesn't have a filename.\nWhat would you like this image to be named?\n> "%(uri,))

        return urllib.unquote(target_filename)
