:title: rst2wp: a ReStructuredText to Wordpress uploader

rst2wp is a Wordpress blogging client. It uses XML-RPC to upload posts.

The basic use case is to enable faster and more automatic blogging than is possible with the HTML/JS interface to Wordpress. To that end, you can use `your favorite editor <http://www.gnu.org/software/emacs/>`_ to write your posts, and then run ``rst2wp post.rst`` to get them online.

Requirements
============

* python-argparse
* python-docutils
* python-xdg

Features
========

- The image:: directive has been customized to upload images using the
  WordPress API. You can give it any URL; if the image is
  non-local, it will be automatically downloaded using urllib.
- Tags and categories are read from bibliographic fields at the top of
  the file. Many
- Complies with the `XDG Base Directory
  <http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_
  spec by default. This means configuration by default goes in
  ``$HOME/.config/rst2wp/``.

Getting started
===============

Just run the script once to create ~/.config/rst2wp/wordpressrc.
Account settings and configuration stuff goes in there.

Usage
=====

Run rst2wp with the name of a post as its argument. The post is just
an ordinary RST file, except that the (normally optional)
bibliographic fields at the top of the file are required in order to
provide a title to the post.

Here's a sample post::

    :title: This is a brand new test!

    This is just a test, of course. Here's an image:

    |my_image|

    I'd like to close with a quote:

        Four score and seven years ago..


    .. |my_image| image:: http://travelogue.betacantrips.com/wp-content/uploads/2009/09/tumblr_kqlgm7DjDq1qz59y9o1_500.gif
       :target: http://travelogue.betacantrips.com/

Once you run rst2wp on this file, the file will be modified. Particularly,
you'll see::

    :id: 362

in the bibliographic fields at the top, and in the `image::` directive, you'll see::

    :saved_as: http://travelogue.betacantrips.com/wp-content/uploads/2009/09/tumblr_kqlgm7DjDq1qz59y9o1_500.gif

In the future, this blog post will be altered instead of new ones
being uploaded, and the uploaded image won't be re-uploaded.

You might find this annoying because you might have to re-load the
file in your text editor, so this information is also saved in
~/.config/rst2wp. You can choose one or the other by editing
config.data_storage.

Options
=======

- ``-n``/``--preview`` will open a browser (using $BROWSER) to let you
  "preview" the HTML you're generating.

- ``--list-tags`` and ``--list-categories`` might be helpful, but
  WordPress will only show those that contain posts.

Known Links
===========

Over time you may find that you refer to some sites over and over
again. ReST has a perfectly effective technique for this: defining external
link targets. If you define a known_links file with the format::

    [http://www.example.com/]
    link = example link

Then you can use it freely in all your posts::

    This is a link to `example link`_. Isn't ReST lovely?

Why ReStructuredText?
=====================

Because I like ReStructuredText.

Some people like Markdown. You can tell because they write about functions like gtk\ *window*\ new. Markdown started as a giant ball of regular expressions to create HTML and it hasn't changed much. It has grown extensions to address some shortcomings, but it isn't very extensible.

Additionally, I like the docutils codebase a lot -- it makes the kinds of customizations I made here very easy.
