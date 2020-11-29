:title: rst2wp: a ReStructuredText to Wordpress uploader

rst2wp is a Wordpress blogging client. It uses XML-RPC to upload posts.

The basic use case is to enable faster and more automatic blogging than is possible with the HTML/JS interface to Wordpress. To that end, you can use `your favorite editor <http://www.gnu.org/software/emacs/>`_ to write your posts, and then run ``rst2wp post.rst`` to get them online.

NOTE: ``rst2wp`` is not exactly deprecated but something close to
it. If you are trying to pick a tool to use on your cool new blog
idea, it would be hard for me to recommend this one. When this program
was first written (in 2009), Wordpress seemed like a good way to
publish a blog-like site with features like tags, RSS feeds, and
search. In that environment, using ``rst2wp`` to facilitate writing
posts as plain text in a git repository made perfect sense. In 2020,
the landscape looks a lot different and it's hard to justify tying
your site to Wordpress as an implementation choice. There's a whole
category of "static site generators" and any of them will be
better-maintained than ``rst2wp``, to say nothing of whether your site
really needs to be running Wordpress on the backend. In particular
I've heard good things about `Pelican
<https://blog.getpelican.com/>`_. The rest of the documentation is
targeted at existing users of ``rst2wp`` who are not motivated to move
their entire site to something else.

Requirements
============

* python-docutils
* python-magic
* `python-pyxdg <https://www.freedesktop.org/wiki/Software/pyxdg/>`_ (not to be confused with `xdg <https://pypi.org/project/xdg/>`_)
* pillow
* You probably also want ``exiftran`` from `fbida <https://www.kraxel.org/blog/linux/fbida/>`_

Features
========

- The image:: directive has been customized to upload images using the
  WordPress API. You can give it any URL; if the image is
  non-local, it will be automatically downloaded using urllib.
- Tags and categories are read from bibliographic fields at the top of
  the file. Many
- Configuration by default goes in ``$HOME/.config/rst2wp/``.

Shortcomings
============

- Unicode filenames and other stuff haven't really been thought through.  I just sprinkled some .encode('utf-8') calls here and there and things seem to work for me.

Getting started
===============

1. ``git clone https://github.com/glasserc/rst2wp.git``
2. ``cd rst2wp``
3. ``python setup.py install``

Then just run ``rst2wp`` once to create ~/.config/rst2wp/wordpressrc.
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

- ``-c``/``--config NAME`` may be of use to you if you maintain
  multiple blogs with rst2wp. At present it lets you use another name
  to look for configs (so you can search ``~/.config/NAME``
  instead of ``~/.config/rst2wp``), but in the future it may be more
  useful somehow.

- ``--list-tags`` and ``--list-categories`` might be helpful, but
  WordPress will only show those that contain posts.

Config
======

The configuration file (by default ``$HOME/.config/rst2wp/wordpressrc``) has several parameters:

- config.data_storage = one of "file", "dotrc", or "both" (default is "file").
  "dotrc" means to store URLs of uploaded images in ~/.config/rst2wp/images
  and ids of posts in ~/.config/rst2wp/posts. "file" means to store that
  information in the .rst file itself. "both" stores in both places,
  and generally trusts the file over the dotrc files.

  "file" is recommended, but in case you don't like rst2wp editing
  your files, "dotrc" is provided. Use "both" if you are indecisive.

  N.B.: if config.data_storage = "dotrc", the filename of the post is
  assumed to be unique across all blog posts. This means if you re-use
  a filename, you could potentially edit an existing blog-post. To
  help guard against this, FIXME: need to check if title is the same
  as what's in the dotrc, and if different, confirm.

- config.publish_default = "yes" or "no" (default is yes). See
  "Publishing", below.

- config.save_uploads = "yes" or "no" (default no). If true, all
  uploaded files are saved to an "uploads/" directory in the same
  directory as the post.

- config.scale_images = [Not implemented yet.]

Publishing
----------

Wordpress supports having posts that aren't yet published. There are many reasons you might do this -- for one, you might want to make sure rst2wp didn't make a hash of your post. Thus, rst2wp can mark a post "published" or not. This is controlled in several ways.

1. If either of the ``--publish``\ /\ ``--no-publish`` arguments are present, this has priority (``--publish`` marks the post published; ``--no-publish`` marks the post as "unpublished").

2. Otherwise, if the post has a bibliographic field called ``:publish:`` and it is set to "yes", the post is marked published.

3. Otherwise, if the configuration parameter ``publish_default`` is set, the value of the parameter is used: "yes" marks the post published, "no" marks it as unpublished.

4. Otherwise, the post is marked as unpublished.

Known Links
-----------

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

Notes on changing Wordpress's themes
====================================

Some CSS styles you might want to drop into your theme's style.css.

::

    .line {
        min-height: 1em;
    }
