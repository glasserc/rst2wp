#!/usr/bin/env python

'''Script to translate rst into HTML and post it to a Wordpress server.

See the README for more details.
'''
# FIXME: robust against missing configuration keys
# FIXME: prompt for a good filename/extension for unknown weird files
# FIXME: if xmlrpc breaks, try to provide a useful error message
# FIXME: .. figure:: directive
# FIXME: progress meter on uploading images/files

import re
import argparse
from xdg import BaseDirectory
import ConfigParser
import sys
import os.path
import tempfile, subprocess, time, datetime
from docutils import core, io, nodes, utils
from docutils.readers import standalone
import docutils.writers.html4css1
import docutils.transforms
#import yaml
import utils

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), "lib"))

import wordpresslib
import my_image # registers MyImageDirective
import upload   # registers UploadDirective
import nodes    # monkeypatches nodes.field_list
import validity
from config import IMAGES_LOCATION, POSTS_LOCATION, TEMP_FILES


class UsageError(Exception):
    @classmethod
    def usage_message(cls):
        return \
'''Usage: {name} filename
Converts an RST file into HTML and posts it to Wordpress.
See the source for more details.'''.format(name=os.path.basename(sys.argv[0]))

    def error_message(self):
        return "{error}\nSee '{path} --help'.".format(error=self.args[0],
                                                      path=self.args[1])


class MyTranslator(docutils.writers.html4css1.HTMLTranslator):
    def visit_image(self, node):
        docutils.writers.html4css1.HTMLTranslator.visit_image(self, node)
        image = self.body[-1]
        # Default title to alt text
        title = node.attributes.get('title', node.attributes.get('alt', None))

        if title:
            # Hackishly insert the image title into the image tag
            self.body[-1] = image.replace('/>', 'title="%s" />'%self.attval(title))

class ValidityCheckerTransform(docutils.transforms.Transform):
    default_priority = 99
    def apply(self):
        fields = self.document.settings.bibliographic_fields
        app = self.document.settings.application

        def _no_field(msg, msg2=''):
            if msg2: msg = msg+msg2
            raise TypeError, msg

        if 'title' not in fields:
            _no_field("title missing", """
- Make sure you have a bibliographic field list at the top of your file.
- Make sure that a title field is included.""")

        if fields['title'] == '':
            _no_field("title empty", """
- Please set a title, because otherwise rst2wp breaks horribly.""")

        if not fields.get('categories'):
            _no_field("No categories supplied", """
WordPress requires at least one category.

If you don't want to categorize this post, use the "Uncategorized" category.

Set config.default_category to do this automatically.

:categories: Uncategorized
""")



class WordPressReader(standalone.Reader):
    def __init__(self, preview=False):
        standalone.Reader.__init__(self)
        self.preview = preview

    def get_transforms(self):
        transforms = standalone.Reader.get_transforms(self)
        if self.preview: return transforms

        transforms.insert(1, ValidityCheckerTransform)
        return transforms


class Application(object):
    '''Container for all dotrc-config-related stuff'''
    config_name = 'rst2wp'
    def __init__(self):
        super(Application, self).__init__()
        self._config = None

    @property
    def config(self):
        if self._config: return self._config
        return self._load_config()

    def _read_configs_into(self, config, filepath='wordpressrc', config_name='config'):
        '''Used to read application config (blog name, etc.)'''
        for dir in BaseDirectory.load_config_paths(self.config_name):
            filename = os.path.join(dir, filepath)
            if not os.path.exists(filename): continue
            print "loading {0} from".format(config_name), filename
            with file(filename) as f:
                config.readfp(f)
            print 'config loaded'

    def _load_config(self):
        config = ConfigParser.SafeConfigParser()
        self.VERBOSE = False

        self._read_configs_into(config)

        DEFAULT_WORDPRESS_URL = 'http://wordpress.example.com/wordpress/xmlrpc.php'

        if not config.has_section('account'):
            config.add_section('account')
            # Fill in some default values
            config.set('account', 'url', DEFAULT_WORDPRESS_URL)
            config.set('account', 'username', 'joe_user')
            config.set('account', 'password', 'trustNo1')

            config.add_section('config')
            config.set('config', 'data_storage', 'file')
            config.set('config', 'publish_default', 'yes')
            config.set('config', 'save_uploads', 'no')
            config.set('config', 'scale_images', 'no')
            config.set('config', 'default_category', 'Uncategorized')
            config.set('config', 'tab_width', 4)
            config.set('config', 'initial_header_level', 2)

            path = os.path.join(BaseDirectory.save_config_path('rst2wp'), 'wordpressrc')
            print 'Need configuration! Edit %s'%(path,)
            with file(path, 'wb') as fp:
                config.write(fp)
            sys.exit()

        if config.get('account', 'url') == DEFAULT_WORDPRESS_URL:
            # Don't wipe out what they might have configured
            print 'Still needs configuration! Edit %s'%(path,)
            sys.exit()

        self._config = config
        return config

    def search_configs(self, configfile, section, key, default=None):
        '''Looks through all configs named configfile for (section, key)'''
        for dir in BaseDirectory.load_config_paths(self.config_name):
            filename = os.path.join(dir, configfile)
            if not os.path.exists(filename): continue

            config = ConfigParser.SafeConfigParser()
            with file(filename) as f:
                config.readfp(f)
            if not config.has_section(section): continue

            if not config.has_option(section, key): continue

            return config.get(section, key)

        return default


class Rst2Wp(Application):
    def _known_link_stanza(self):
        known_links = ConfigParser.SafeConfigParser()
        self._read_configs_into(known_links, 'known_links', 'known links')

        links = []
        for sectname in known_links.sections():
            links.append('.. _`{name}`: {link}'.format(link=sectname,
                                                       name=known_links.get(sectname, 'link')))

        return '\n\n'+'\n'.join(links)

    def __init__(self):
        super(Rst2Wp, self).__init__()
        self.preview = False
        self.list_tags = False
        self.list_categories = False
        self.publish = None

    @property
    def data_storage(self):
        return self.config.get('config', 'data_storage')

    def parse_args(self, args):
        parser = argparse.ArgumentParser(description=
                                         'Convert ReStructuredText to HTML and upload to a Wordpress instance.')
        parser.add_argument('-n', '--preview', action='store_true',
                            help="don't upload; render to HTML and display in $BROWSER")
        parser.add_argument('-c', '--config', dest='alt_config', nargs='?', type=str,
                            help='use alternate config (see README for details)')
        parser.add_argument('--dont-check-tags', action='store_true',
                            help="don't check categories/tags for existance")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('filename', type=str, nargs='?',
                            help='the ReStructuredText source file (optional if querying tags/categories)')
        group.add_argument('--list-tags', action='store_true',
                            help="list available tags for this Wordpress instance")
        group.add_argument('--list-categories', action='store_true',
                            help="list available categories for this Wordpress instance")

        group = parser.add_mutually_exclusive_group()
        group.add_argument('--publish', action='store_const', const=True,
                           help="mark this post as published")
        group.add_argument('--no-publish', dest='publish', action='store_const', const=False,
                           help="do not mark this post as published")

        options = parser.parse_args(args, self)
        if isinstance(self.alt_config, str): self.config_name = self.alt_config

    def prompt(self, msg):
        return raw_input(msg)

    def save_post_info(self, document, key, value):
        data_storage = self.data_storage
        if data_storage in ['both', 'dotrc']:
            section = 'post ' + self.filename
            self._save_config_info(section, key, value)

        if data_storage in ['both', 'file']:
            self.replace_field(document, key, value)

        self._save_post_updated()

    def save_directive_info(self, document, directive, url, key, value):
        data_storage = self.data_storage
        if data_storage in ['both', 'dotrc']:
            section = directive + ' ' + url
            self._save_config_info(section, key, value, location=IMAGES_LOCATION)

        if data_storage in ['both', 'file']:
            self.replace_directive(document, directive, url, key, value)
            # Also update document.settings with the new info.
            document.settings.directive_uris[directive][url+'.'+key] = value

        self._save_post_updated()

    def _save_config_info(self, section, key, value, location=None):
        location = location or POSTS_LOCATION
        config = ConfigParser.SafeConfigParser()
        filename = location()
        if os.path.exists(filename):
            with file(filename) as f:
                config.readfp(f)

        if not config.has_section(section):
            config.add_section(section)

        config.set(section, key, value)
        with file(filename, 'wb') as fp:
            config.write(fp)

    def _save_post_updated(self):
        # Save immediately, so as to not forget the location of an uploaded image
        if self.should_save_file():
            print "Saving file with new data"
            file(self.filename, 'w').write(self.text)

    def get_post_info(self, document, key):
        '''Get stored information about a post.

        For data_storage=file, this means look at the bibliographic
        fields. For data_storage=dotrc, this means look through the
        POSTS_LOCATION file and try to find the section about the post.'''
        if self.data_storage in ['both', 'file']:
            return document.settings.bibliographic_fields[key]

        # FIXME: use document to get filename?
        section = "post " + self.filename
        return self.search_configs(POSTS_LOCATION(), section, key)

    def get_directive_info(self, document, directive, url, key):
        '''Get info about a certain directive (for example, the uploaded_form for an image:: directive).

        For data_storage=file, this information is stored as an option
        in the directive itself, which are then read into
        document.settings.directive_uris.  For data_storage=dotrc, it
        is stored under a correspondingly-named section in
        IMAGES_LOCATION.
        '''
        # Of course, this only really works with single-argument
        # directives.
        if self.data_storage in ['both', 'file']:
            try:
                return document.settings.directive_uris[directive][url+'.'+key]
            except KeyError:
                pass
            if self.data_storage == 'file':
                raise ValueError, "uh oh.. don't know what the image URI should be for {uri}".format(uri=url)

        section = directive + ' ' + url
        return self.search_configs(location(), section, key)

    def has_post_info(self, document, key):
        if self.data_storage in ['both', 'file']:
            return key in document.settings.bibliographic_fields

        section = 'post ' + self.filename
        return self._has_config_info(document, section, key)

    def has_directive_info(self, document, directive, url, key):
        if self.data_storage in ['both', 'file']:
            try:
                return document.settings.directive_uris[directive][url+'.'+key]
            except KeyError:
                pass

        return self._has_config_info(document, directive + ' ' + url, key, location=IMAGES_LOCATION)

    def _has_config_info(self, document, section, key, location=POSTS_LOCATION):
        class NO_DEFAULT:
            pass

        return self.search_configs(location(), section, key, NO_DEFAULT) is not NO_DEFAULT


    def replace_field(self, document, key, value):
        '''Inserts a bibliographic field into the header of an RST document.

        Replaces an existing field of the same name.'''
        keystring = ':{key}:'.format(key=key)
        new_line = '{keystring} {value}'.format(keystring=keystring, value=value.encode('utf8'))

        # Add field after other fields, or replace if exists
        in_fields = False
        lines = self.text.split('\n')
        for i in range(len(lines)):
            if ':' == lines[i][:1]:
                in_fields = True
            if not in_fields: continue
            if '' == lines[i].strip():
                # Didn't have that field
                lines.insert(i, new_line)
                break
            if lines[i].startswith(keystring):
                lines[i] = new_line
                break

        self.text = '\n'.join(lines)

    def get_indent(self, s):
        r = re.compile('^\s*')
        m = r.search(s)
        return m.end()

    def replace_directive(self, document, directive, uri, key, value):
        '''Add a field to a URL-based directive.'''
        r = re.compile('{name}::\s+({uri})'.format(name=directive, uri = re.escape(uri.encode('utf-8'))))
        lines = self.text.split('\n')

        for i in range(len(lines)):
            if r.search(lines[i]):
                n = self.get_indent(lines[i])
                # FIXME: check if it's already there
                lines.insert(i+1, ((n+3)*' ')+':{key}: {value}'.format(key=key, value=value.encode('utf-8')))

        self.text = '\n'.join(lines)

    def should_save_file(self):
        data_storage = self.config.get('config', 'data_storage')
        save_to_file = data_storage in ['both', 'file']
        return self.text != file(self.filename).read() and save_to_file

    def create_client(self, url, username, password):
        wp = wordpresslib.WordPressClient(url, username, password)
        config = self.config

        if not config.has_option('account', 'blog_id') or config.get('account', 'blog_id') == '':
            blogs = list(wp.get_users_blogs())
            blog = blogs[0]
            print "Arbitrarily picking first blog: %s at %s"%(blog.name, blog.url)
            wp.selectBlog(blog.id)
        else:
            blog_id = config.get_int('account', 'blog_id')
            print "Using blog id %s from config" % (blog_id,)
            wp.selectBlog(blog_id)

        return wp

    def run(self, *args, **kwargs):
        if not args: args = sys.argv[1:]
        self.parse_args(args)
        config = self.config

        url = config.get('account', 'url')
        username = config.get('account', 'username')
        password = config.get('account', 'password')
        if config.has_option('account', 'verbose'):
            self.VERBOSE = config.get('account', 'verbose')

        print "Connecting to WP server at", url
        wp = None
        if not self.preview:
            self.wp = wp = self.create_client(url, username, password)

        if self.VERBOSE:
            options = wp.get_options()
            print "Talking to %s version %s"%(options['software_name'], options['software_version'])

        if not self.preview:
            if self.list_tags:
                return self.run_list_tags()
            elif self.list_categories:
                return self.run_list_categories()

        with file(self.filename) as f:
            self.text = text = f.read()

        # self.text is the version we eventually save;
        # text is the version we render
        text = text+self._known_link_stanza()
        reader = WordPressReader(self.preview)

        used_images = {}
        writer = docutils.writers.html4css1.Writer()
        writer.translator_class = MyTranslator

        directive_uris = {'image': {}, 'upload': {}}

        categories = [self.config.get('config', 'default_category')]
        if not self.dont_check_tags and not self.preview:
            validity.Validity.verify_categories(wp, categories)

        # Source path is for use include directive in rst file
        output = core.publish_parts(source=text, writer=writer,
                                    source_path=os.path.abspath(self.filename),
                                    reader=reader,
                                    settings_overrides={
                'wordpress_instance' : wp,
                'application': self,
                'bibliographic_fields': {
                    'categories': categories
                    },
                'directive_uris': directive_uris,
                'used_images': used_images,
                # FIXME: probably a nicer way to do this
                'filename': self.filename,
                'tab_width' : int(self.config.get('config', 'tab_width')),
                'initial_header_level' : int(self.config.get('config', 'initial_header_level')),
                })
        #print yaml.dump(output, default_flow_style=False)
        body = output['body']

        if self.preview:
            return self.run_preview(output)


        fields = reader.document.settings.bibliographic_fields

        categories = [wordpresslib.WordPressCategory(name=cat) for cat in fields['categories']]
        tags = []
        for tag in fields.get('tags', []):
            if wp.has_tag(tag):
                tags.append(wp.get_tag(tag))
            else:
                tags.append(wordpresslib.WordPressTag(name=tag))
        # WP will replace \n with <br/>, which isn't what RST is
        # designed for. We short-circuit this by replacing all newlines
        # with spaces, which ought to be safe.
        body = utils.replace_newlines(body)

        new_post_data = {
            'title' : unicode(fields['title']),
            'categories': categories,
            'tags': tags,
            'description': body,
            }

        if self.has_post_info(reader.document, 'id'):
            new_post = False
            post_id = self.get_post_info(reader.document, 'id')
            post_id = unicode(post_id)
            post = wp.get_post(post_id)
        else:
            new_post = True
            post = None

        # Post date
        # 1. Set bibliogrphic fields :date: in rst file
        # 2. New post will auto set if no :date: field
        # 3. Old post will retrieve publish and set
        # 4. Set :date: can only change in rst file manually
        # 5. :date: is NOT post last modify time, it's publish time in local dz
        if not 'date' in fields:
            if new_post:
                new_post_data['date'] = time.localtime()
            else:
                # Convert post time in UTC to localtime
                new_post_data['date'] = time.localtime(time.mktime(post.date) - time.timezone)
            # Write :date: field
            self.save_post_info(reader.document, 'date', time.strftime("%Y-%m-%d %H:%M:%S", new_post_data['date']))
        else:
            new_post_data['date'] = datetime.datetime.strptime(fields['date'], '%Y-%m-%d %H:%M:%S').timetuple()

        # Publish priority:
        # 1. --publish/--no-publish
        # 2. :publish: yes
        # 3. config publish_default
        # 4. default to false
        publish = None
        if publish == None: publish = self.publish
        if publish == None:
            publish = fields.get('publish', None)
            if publish == 'yes': publish = True
            if publish == 'no': publish = False
        if publish == None and config.has_option('config', 'publish_default'):
            publish = config.getboolean('config', 'publish_default')
        if publish == None: publish = False

        if not new_post:
            post.__dict__.update(new_post_data)

            if fields.get('type') == 'page':
                wp.edit_page(post_id, post, publish)
            else:
                wp.edit_post(post_id, post, publish)

        else:
            user = wp.get_user_info()
            new_post_data['user'] = user.id
            post = wordpresslib.WordPressPost(**new_post_data)

            if fields.get('type') == 'page':
                post_id = wp.new_page(post, publish)
            else:
                post_id = wp.new_post(post, publish)
            self.save_post_info(reader.document, 'id', str(post_id))

        self.save_post_info(reader.document, 'title', fields['title'])

        # Print end messange and preview link
        print
        print 'Done, url for preview with permaLink:'
        print post.permaLink + '&preview=true'

        # No idea why I even wrote this in the first place.
        # for image_uri in used_images:
        #     self.save_directive_info(reader.document, "image", image_uri,
        #                    'used in ' + str(post_id), fields['title'])

    def run_preview(self, output):
        body = output['body']
        fp = tempfile.NamedTemporaryFile(suffix='-rst2wp-preview.html',
                                         delete=False)
        fp.write(body.encode('utf8'))
        fp.close()
        browser = os.getenv('BROWSER') or 'sensible-browser'
        subprocess.call([browser, fp.name])
        # FIXME: better way to know when it gets loaded?
        time.sleep(5)

        os.unlink(fp.name)

    def run_list_tags(self):
        tags = self.wp.get_tags()
        for tag in tags:
            print '{name} (id {id}): {count} posts'.format(**tag.__dict__)

    def run_list_categories(self):
        categories = self.wp.get_categories()
        for category in categories:
            print '{name} (id {id})'.format(**category.__dict__)

if __name__ == '__main__':
    try:
        Rst2Wp().run()
    except UsageError, u:
        print u.error_message()
        sys.exit(1)
    finally:
        for filename in TEMP_FILES:
            os.unlink(filename)
