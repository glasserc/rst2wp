#Strategy here: monkeypatch some docutils node classes, specifically
#field_list and field, so that we can

import docutils.nodes
import utils

raw_input = __builtins__['raw_input']
old_field_list = docutils.nodes.field_list

class  rst2wp_field_list(old_field_list):
    # Catch when new fields are added, and parse them, and store them
    def append(self, child):
        old_field_list.append(self, child)

        field_name, field_value = self.parse_field(child)
        if field_name == 'tag':
            field_name = 'tags'
            field_value = utils.list_wrap(field_value)
        if field_name == 'category':
            field_name = 'categories'
            field_value = utils.list_wrap(field_value)

        self.store_field(field_name, field_value)

    def parse_field(self, child):
        field_name, field_value = child.children
        assert len(field_name.children) == 1, "don't know how to handle"
        assert isinstance(field_name.children[0], docutils.nodes.Text)
        key = field_name.children[0].astext()

        # field_body is a node with either a bulleted_list child, or
        # a single Text child, or..?
        if len(field_value.children) == 0:
            return key, None

        assert len(field_value.children) == 1, "don't know how to handle"
        data = field_value.children[0]
        if isinstance(data, docutils.nodes.bullet_list):
            value = [node.astext() for node in data.children]
        elif isinstance(data, docutils.nodes.Text):
            value = data.astext()
        elif isinstance(data, docutils.nodes.paragraph):
            value = data.children[0].astext()
        else:
            raise TypeError, "don't know how to handle a %s in the header %s"%(
                data.__class__, key)

        return key, value

    def store_field(self, key, value):
        fields = self.document.settings.fields
        fields[key] = value

        # Check if there is a wordpress_instance, and there is either
        # no application, or an application with dont_check_tags ==
        # False).
        # i.e. check if it's possible and not forbidden.
        if getattr(self.document.settings, 'wordpress_instance', None) and \
                (not hasattr(self.document.settings, 'application') or \
                not self.document.settings.application.dont_check_tags):
            # Verify validity of tags/categories
            if key == 'tags':
                self.verify_tags(value)

            if key == 'categories':
                self.verify_categories(value)

    def verify_tags(self, tags):
        if not isinstance(tags, list): tags = [tags]
        for tag in tags:
            self.check_existing_tag(self.document.settings.wordpress_instance, tag)

    def verify_categories(self, categories):
        if not isinstance(categories, list): categories = [categories]
        for category in categories:
            self.check_existing_category(self.document.settings.wordpress_instance, category)

    def check_existing_tag(self, wp, tag):
        if ',' in tag:
            raise ValueError, """Cannot use tags with ',' in the name.

WordPress will break tags at commas. If you really want a tag with a comma, add it via the web interface."""
        if not wp.has_tag(tag):
            tag = self.read_tag(tag)

    def check_existing_category(self, wp, cat):
        if not wp.has_category(cat):
            cat = self.read_category(cat)

    def read_base(self, name):
        fmt = {'name': repr(str(name))}
        slug = raw_input("Slug for {name} [auto-generate]: ".format(**fmt))
        description = raw_input("Description for {name} [none]: ".format(**fmt))
        return {'slug': slug, 'description': description, 'name': name}

    def read_tag(self, tag):
        fmt = {'tag': repr(str(tag))}
        if ',' in tag:
            raise ValueError, """Cannot create tag with ',' in the name.

If you really want a tag with a comma in the name, create it via the web interface first."""

        print "Post has non-existent tag {tag}. Ctrl-C to cancel.".format(**fmt)
        print "rst2wp can create the tag automatically, but can't set description or slug via XML-RPC API. If you want to edit these things, log in to the blog!"
        raw_input("Confirm creation? [yes] ")

    def read_category(self, cat):
        fmt = {'category': repr(str(cat))}
        print "Post has non-existent category {category}. Ctrl-C to cancel.".format(**fmt)
        raw_input("Confirm? [yes]")

        data = self.read_base(cat)
        parent_id = raw_input("Parent id for {category} [none]: ".format(**fmt))

        c = wordpresslib.WordPressCategory(parent_id=parent_id, **data)
        wp.new_category(c)


docutils.nodes.field_list = rst2wp_field_list
