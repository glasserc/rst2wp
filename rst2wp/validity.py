'''Validity module.

Encapsulates logic for whether to check existence of tags/categories,
and how to check it based on a document.'''
from __future__ import print_function
raw_input = __builtins__['raw_input']

class Validity(object):
    @classmethod
    def should_check(cls, document):
        # Check if there is a wordpress_instance, and there is either
        # no application, or an application with dont_check_tags ==
        # False).
        if getattr(document.settings, 'wordpress_instance', None) and \
                (not hasattr(document.settings, 'application') or \
                not document.settings.application.dont_check_tags):
            return True
        return False


    @classmethod
    def maybe_verify_tags(cls, document, tags):
        if not cls.should_check(document): return

        cls.verify_tags(document.settings.wordpress_instance, tags)

    @classmethod
    def verify_tags(cls, wp, tags):
        if not isinstance(tags, list): tags = [tags]
        for tag in tags:
            cls.check_existing_tag(wp, tag)

    @classmethod
    def maybe_verify_categories(cls, document, categories):
        if not cls.should_check(document): return

        cls.verify_categories(document.settings.wordpress_instance, categories)

    @classmethod
    def verify_categories(cls, wp, categories):
        if not isinstance(categories, list): categories = [categories]
        for category in categories:
            cls.check_existing_category(wp, category)

    @classmethod
    def check_existing_tag(cls, wp, tag):
        if ',' in tag:
            raise ValueError("""Cannot use tags with ',' in the name.

WordPress will break tags at commas. If you really want a tag with a comma, add it via the web interface.""")
        if not wp.has_tag(tag):
            tag = cls.read_tag(tag)

    @classmethod
    def check_existing_category(cls, wp, cat):
        if not wp.has_category(cat):
            cat = cls.read_category(wp, cat)

    @classmethod
    def read_base(cls, name):
        fmt = {'name': repr(str(name))}
        slug = input("Slug for {name} [auto-generate]: ".format(**fmt))
        description = input("Description for {name} [none]: ".format(**fmt))
        return {'slug': slug, 'description': description, 'name': name}

    @classmethod
    def read_tag(cls, tag):
        fmt = {'tag': repr(str(tag))}
        if ',' in tag:
            raise ValueError("""Cannot create tag with ',' in the name.

If you really want a tag with a comma in the name, create it via the web interface first.""")

        print("Post has non-existent tag {tag}. Ctrl-C to cancel.".format(**fmt))
        print("rst2wp can create the tag automatically, but can't set description or slug via XML-RPC API. If you want to edit these things, log in to the blog!")
        input("Confirm creation? [yes] ")

    @classmethod
    def read_category(cls, wp, cat):
        fmt = {'category': repr(str(cat))}
        print("Post has non-existent category {category}. Ctrl-C to cancel.".format(**fmt))
        input("Confirm? [yes]")

        data = cls.read_base(cat)
        parent_id = input("Parent id for {category} [none]: ".format(**fmt))

        c = wordpresslib.WordPressCategory(parent_id=parent_id, **data)
        wp.new_category(c)
