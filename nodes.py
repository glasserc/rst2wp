#Strategy here: monkeypatch some docutils node classes, specifically
#field_list and field, so that we can

import docutils.nodes

old_field_list = docutils.nodes.field_list

class rst2wp_field_list(old_field_list):
    def setup_child(self, child):
        old_field_list.setup_child(self, child)

    def append(self, child):
        old_field_list.append(self, child)

        self.store_field(child)

    def store_field(self, child):
        fields = self.document.settings.fields

        field_name, field_value = child.children
        assert len(field_name.children) == 1, "don't know how to handle"
        assert isinstance(field_name.children[0], docutils.nodes.Text)
        key = field_name.children[0].astext()

        # field_body is a node with either a bulleted_list child, or
        # a single Text child, or..?
        if len(field_value.children) == 0:
            fields[key] = None
            return

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

        fields[key] = value

docutils.nodes.field_list = rst2wp_field_list
