#Strategy here: monkeypatch some docutils node classes, specifically
#field_list and field, so that we can

import docutils.nodes
import utils, validity

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
        fields = self.document.settings.bibliographic_fields
        fields[key] = value

        # Verify validity of tags/categories
        if key == 'tags':
            validity.Validity.maybe_verify_tags(self.document, value)

        if key == 'categories':
            validity.Validity.maybe_verify_categories(self.document, value)

docutils.nodes.field_list = rst2wp_field_list
