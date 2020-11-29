"""
    wordpresslib.py

    WordPress xml-rpc client library
    use MovableType API

    Copyright (C) 2005 Michele Ferretti
    black.bird@tiscali.it
    http://www.blackbirdblog.it

    With some additions by Ethan Glasser-Camp
    ethan.glasser.camp@gmail.com
    http://www.betacantrips.com

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA       02111-1307, USA.

    XML-RPC supported methods:
        * getUsersBlogs
        * getUserInfo
        * getPost
        * getRecentPosts
        * newPost
        * editPost
        * deletePost
        * newMediaObject
        * getCategoryList
        * getPostCategories
        * setPostCategories
        * getTrackbackPings
        * publishPost
        * getPingbacks
        * newCategory

    References:
        * http://codex.wordpress.org/XML-RPC_Support
        * http://www.sixapart.com/movabletype/docs/mtmanual_programmatic.html
        * http://docs.python.org/lib/module-xmlrpclib.html
"""
from __future__ import print_function

__author__ = "Michele Ferretti <black.bird@tiscali.it>"
__copyright__ = "Copyright (c) 2005 Michele Ferretti"
__license__ = "LGPL"

import exceptions
import re
import os
import xmlrpc.client
import datetime
import time
from functools import wraps
import mimetypes
import warnings

class WordPressException(exceptions.Exception):
    """Custom exception for WordPress client operations
    """
    def __init__(self, obj):
        if isinstance(obj, xmlrpc.client.Fault):
            self.id = obj.faultCode
            self.message = obj.faultString
        else:
            self.id = 0
            self.message = obj

    def __str__(self):
        return '<%s %d: \'%s\'>' % (self.__class__.__name__, self.id, self.message)

# N.B. The wordpress API is not especially consistent. Here are some notes:

# Blogger.getPost vs. metaWeblog.getPost. Blogger API was superceded
# by metaWeblog API. The Blogger API only allows a single "string"
# content, and parses the crap out of it; only allows one category;
# etc.

# Passing categories: there are different APIs with different
# interfaces.  You should be able to pass an array of category names
# to newPost/editPost, but mt.setPostCategories wants an array of ids
# and a field called isPrimary (isPrimary is ignored by WP).

# Timezones aren't really dealt with; when getting a post, we use
# date_created_gmt and post back using date_created_gmt. This is at
# least consistent; when you post back using dateCreated it seems to
# interpret this as GMT, even though when you read dateCreated it
# seems to be in the local timezone. It isn't clear if this is by
# design or what, but other people seem to have run into similar issues:
#
# http://www.simmonsconsulting.com/2008/02/29/daylight-saving-time-and-wordpress-xmlrpc/

class WordPressBlog(object):
    """Represents blog item
    """
    def __init__(self, id=None, name=None, url=None, isAdmin=None):
        self.id = id or ''
        self.name = name or ''
        self.url = url or ''
        self.isAdmin = isAdmin or False

    @classmethod
    def from_xmlrpc(cls, blog):
        return cls(
            id      = blog['blogid'],
            name    = blog['blogName'],
            isAdmin = blog['isAdmin'],
            url     = blog['url'],
            )


class WordPressUser(object):
    """Represents user item
    """
    def __init__(self, id=None, firstname=None, lastname=None, nickname=None,
                 email=None):
        self.id = id or ''
        self.firstname = firstname or ''
        self.lastname = lastname or ''
        self.nickname = nickname or ''
        self.email = email or ''

    def get_firstName(self):
        warnings.warn('firstName is deprecated; use firstname',
                      DeprecationWarning)
        return self.firstname
    firstName = property(get_firstName)

    def get_lastName(self):
        warnings.warn('lastName is deprecated; use lastname',
                      DeprecationWarning)
        return self.lastname
    lastName = property(get_lastName)

    @classmethod
    def from_xmlrpc(cls, userinfo):
        return cls(
            id        = userinfo['userid'],
            firstname = userinfo['firstname'],
            lastname  = userinfo['lastname'],
            nickname  = userinfo['nickname'],
            email     = userinfo.get('email', '') # FIXME: ?
            )


class CategoryBase(object):
    """Base class for both categories and tags
    """

    def __init__(self, id=None, name=None, description=None, slug=None,
                 html_url=None, rss_url=None):
        self.id = id or None
        self.name = name or ''
        self.description = description or ''
        self.slug = slug or ''
        self.html_url = html_url
        self.rss_url = rss_url

    def __repr__(self):
        id_badge = '(id unknown)'
        if self.id != None:
            id_badge = '(id=%s)'%(self.id)

        return '<%s %r %s at %#x>'%(self.__class__.__name__, self.name, id_badge, id(self))

class WordPressTag(CategoryBase):
    def __init__(self, id=None, name=None, description=None, count=None, slug=None, html_url=None, rss_url=None):
        super(WordPressTag, self).__init__(id=id, name=name, description=description,
                                           slug=slug, html_url=html_url, rss_url=rss_url)
        self.count = count or 0

    @classmethod
    def from_xmlrpc(cls, tag):
        return cls(id          = int(tag['term_id']),
                   name        = tag['name'],
                   count       = int(tag['count']),
                   slug        = tag['slug'],
                   html_url    = tag.get('html_url'),
                   rss_url     = tag.get('rss_url'),
                   )

class WordPressCategory(CategoryBase):
    """Represents category item
    """
    def __init__(self, id=None, name=None, description=None, slug=None, parent_id=None, html_url=None, rss_url=None):
        super(WordPressCategory, self).__init__(id=id, name=name, description=description, slug=slug, html_url=html_url, rss_url=rss_url)
        self.parent_id = parent_id or '0'  # '0' means no parent

    @classmethod
    def from_xmlrpc(cls, cat):
        return cls(id          = int(cat['term_id']),
                   name        = cat['name'],
                   description = cat['description'],
                   slug        = cat['slug'],
                   parent_id   = cat['parent'],
                   html_url    = cat.get('htmlUrl'),
                   rss_url     = cat.get('rssUrl'),
                   )

    def to_xmlrpc(self):
        data = {'name': self.name,
                'description': self.description,
                'slug': self.slug,
                'parent_id': self.parent_id}

        return data

class WordPressPost(object):
    """Represents post item
    """
    def __init__(self, id=None, title=None, date=None, permaLink=None,
                 description=None, textMore=None, excerpt=None, link=None,
                 categories=None, tags=None, user=None, allowPings=None,
                 allowComments=None):
        self.id = id or None  # indicates not-yet-saved
        self.title = title or ''
        self.date = date or None
        self.permaLink = permaLink or ''
        self.description = description or ''
        self.textMore = textMore or ''
        self.excerpt = excerpt or ''
        self.link = link or ''
        self.categories = categories or []
        self.tags = tags or []
        self.user = user or ''  # N.B. userid as string
        self.allowPings = allowPings or False
        self.allowComments = allowComments or False


def wordpress_call(func):
    '''Decorator that handles the try/catch XMLRPC wrapping'''
    @wraps(func)
    def call(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except xmlrpc.client.Fault as fault:
            raise WordPressException(fault)

    return call

class WordPressClient(object):
    """Client for connect to WordPress XML-RPC interface
    """

    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.blogId = 0
        self.categories = None
        self.tags = None
        self._server = xmlrpc.client.ServerProxy(self.url)

    def _filterPost(self, post):
        """Transform post struct in WordPressPost instance
        """
        postObj = WordPressPost()
        postObj.permaLink       = post['permaLink']
        postObj.description     = post['description']
        postObj.title           = post['title']
        postObj.excerpt         = post['mt_excerpt']
        postObj.user            = post['userid']
        postObj.date            = time.strptime(str(post['date_created_gmt']), "%Y%m%dT%H:%M:%S")
        print("Parsing date:", postObj.date, post['dateCreated'])
        postObj.link            = post['link']
        postObj.textMore        = post['mt_text_more']
        postObj.allowComments   = post['mt_allow_comments'] == 1
        postObj.id              = int(post['postid'])
        categories = []
        for catname in post['categories']:
            categories.append(WordPressCategory(name=catname))

        postObj.categories      = categories
        postObj.allowPings      = post['mt_allow_pings'] == 1
        return postObj

    def _filterCategory(self, cat):
        """Transform category struct in WordPressCategory instance
        """
        return WordPressCategory.from_xmlrpc(cat)

    def selectBlog(self, blogId):
        # FIXME: this doesn't seem very pythonic
        self.blogId = blogId

    def supportedMethods(self):
        """Get supported methods list
        """
        # N.B. not _server.system.listMethods, because that includes
        # the 'standard' XML-RPC methods like system.listMethods,
        # system.listCapabilities, etc.
        return self._server.mt.supportedMethods()

    supported_methods = supportedMethods

    @wordpress_call
    def get_options(self):
        return self._server.wp.getOptions(self.blogId, self.user, self.password)

    getOptions = get_options

    def getLastPost(self):
        """Get last post
        """
        return tuple(self.getRecentPosts(1))[0]

    get_last_post = getLastPost

    @wordpress_call
    def getRecentPosts(self, numPosts=5):
        """Get recent posts
        """
        posts = self._server.metaWeblog.getRecentPosts(self.blogId, self.user,
                                                       self.password, numPosts)
        for post in posts:
            yield self._filterPost(post)

    get_recent_posts = getRecentPosts

    @wordpress_call
    def getPost(self, postId):
        """Get post item
        """
        return self._filterPost(self._server.metaWeblog.getPost(str(postId), self.user, self.password))

    get_post = getPost

    @wordpress_call
    def getUserInfo(self):
        """Get user info
        """
        userinfo = self._server.blogger.getUserInfo('', self.user, self.password)
        return WordPressUser.from_xmlrpc(userinfo)

    get_user_info = getUserInfo

    @wordpress_call
    def getUsersBlogs(self):
        """Get blog's users info
        """
        blogs = self._server.blogger.getUsersBlogs('', self.user, self.password)
        for blog in blogs:
            blogObj = WordPressBlog.from_xmlrpc(blog)
            yield blogObj

    get_users_blogs = getUsersBlogs

    def newPost(self, post, publish):
        """Insert new post

        See the documentation for editPost.
        """
        id = int(self._save_post('metaWeblog', 'newPost', [self.blogId], post, publish))
        post.id = id
        return id

    new_post = newPost

    def newPage(self, page, publish):
        # FIXME: probably wrong
        id = int(self._save_post('wp', 'newPage', [self.blogId], page, publish))
        page.id = id
        return id

    new_page = newPage

    def editPost(self, postId, post, publish):
        """Save post.

        The post's categories are sent as names. If the names aren't
        recognized, they are silently dropped (on the server side).

        @param publish True if you want to also publish this post
        """
        result = self._save_post('metaWeblog', 'editPost', [postId], post, publish)
        if result == 0:
            raise WordPressException('Post edit failed')
        return result

    edit_post = editPost

    def editPage(self, pageId, post, publish):
        '''FIXME: hacked up extremely roughly'''
        result = self._save_post('wp', 'editPage', [self.blogId, pageId], post, publish)
        if result == 0:
            raise WordPressException('Post edit failed')
        return result

    edit_page = editPage

    def _save_post(self, namespace, method_name, args, post, publish):
        blogContent = {
            'title' : post.title,
            'description' : post.description,
            'permaLink' : post.permaLink,
            'mt_allow_pings' : post.allowPings,
            'mt_text_more' : post.textMore,
            'mt_excerpt' : post.excerpt,
            'mt_keywords': self._marshal_tags_names(post.tags),
            'categories' : self._marshal_categories_names(post.categories),
        }

        if post.date:
            # Convert date to UTC
            blogContent['date_created_gmt'] = xmlrpc.client.DateTime(time.gmtime(time.mktime(post.date)))
            print("Back-converting dateCreated:", post.date, blogContent['date_created_gmt'])

        # Get remote method: e.g. self._server.metaWeblog.editPost
        ns = getattr(self._server, namespace)
        meth = getattr(ns, method_name)
        # call remote method: arg0 is blogId for newPost, postId for editPost
        result = meth(*(args+[self.user, self.password, blogContent, int(publish)]))

        return result

    def _marshal_categories_ids(self, categories):
        for c in categories:
            if c.id == -1:
                raise TypeError("bad mojo -- categories need IDs")
        return [{'categoryId': cat.id} for cat in categories]

    def _marshal_tags_names(self, tags):
        tag_data = []
        for tag in tags:
            # This would have hopefully allowed you use existing tags
            # even if they had funny names. OH WELL.
#             if tag.id:
#                 tag_data.append(str(tag.id))
#             else:
            tag_data.append(tag.name)
        return ','.join(tag_data)

    def _marshal_categories_names(self, categories):
        return [cat.name for cat in categories]

    @wordpress_call
    def getPostCategories(self, postId):
        """Get post's categories
        """
        categories = self._server.mt.getPostCategories(postId, self.user,
                                                self.password)
        for cat in categories:
            yield self._filterCategory(cat)

    get_post_categories = getPostCategories

    @wordpress_call
    def setPostCategories(self, postId, categories):
        """Set post's categories.

        @param categories is an array of IDs.
        """
        self._server.mt.setPostCategories(postId, self.user, self.password, categories)

    set_post_categories = setPostCategories

    @wordpress_call
    def newCategory(self, category, parent=None):
        """Create a new category and get its id.

        @param category the category to create
        @param parent (optional) the id or category to create a child of. You can also set parent_id on category.
        @returns the new category
        """
        data = category.to_xmlrpc()
        if parent:
            if isinstance(parent, WordPressCategory):
                parent = parent.id
            data['parent_id'] = parent

        id = self._server.wp.newCategory(self.blogId, self.user, self.password,
                                         data)
        category.id = id
        return category

    new_category = newCategory

    @wordpress_call
    def deletePost(self, postId):
        """Delete post
        """
        return self._server.blogger.deletePost('', postId, self.user,
                                         self.password)

    delete_post = deletePost

    @wordpress_call
    def getCategoryList(self):
        """Get blog's categories list
        """
        warnings.warn('getCategoryList is deprecated; use getCategories instead',
                      DeprecationWarning, 3)
        if not self.categories:
            self.categories = []
            categories = self._server.mt.getCategoryList(self.blogId,
                                            self.user, self.password)
            for cat in categories:
                self.categories.append(self._filterCategory(cat))

        return self.categories

    get_category_list = getCategoryList

    @wordpress_call
    def getCategories(self):
        '''Returns more data then getCategoryList, including description'''
        if not self.categories:
            self.categories = []
            categories = self._server.wp.getTerms(self.blogId,
                                                  self.user,
                                                  self.password,
                                                  'category',
                                                  {'hide_empty': 0})
            for cat in categories:
                self.categories.append(self._filterCategory(cat))

        return self.categories

    get_categories = getCategories

    @wordpress_call
    def getTags(self):
        if not self.tags:
            self.tags = []
            tags = self._server.wp.getTerms(self.blogId,
                                            self.user,
                                            self.password,
                                            'post_tag',
                                            {'hide_empty': 0})

            for t in tags:
                self.tags.append(WordPressTag.from_xmlrpc(t))

        return self.tags

    get_tags = getTags

    def getCategoryIdFromName(self, name):
        """Get category id from category name
        """
        for c in self.getCategories():
            if c.name == name:
                return c.id

    get_category_id_from_name = getCategoryIdFromName

    def getTagIdFromName(self, name):
        for t in self.getTags():
            if t.name == name:
                return t.id

    get_tag_id_from_name = getTagIdFromName

    def getTag(self, name):
        for t in self.getTags():
            if t.name == name:
                return t

    get_tag = getTag

    def has_category(self, name):
        return self.getCategoryIdFromName(name) != None

    def has_tag(self, name):
        return self.getTagIdFromName(name) != None

    @wordpress_call
    def getTrackbackPings(self, postId):
        """Get trackback pings of post
        """
        return self._server.mt.getTrackbackPings(postId)

    get_trackback_pings = getTrackbackPings

    @wordpress_call
    def publishPost(self, postId):
        """Publish post
        """
        return (self._server.mt.publishPost(postId, self.user, self.password) == 1)

    publish_post = publishPost

    @wordpress_call
    def getPingbacks(self, postUrl):
        """Get pingbacks of post
        """
        return self._server.pingback.extensions.getPingbacks(postUrl)

    get_pingbacks = getPingbacks

    def newMediaObject(self, mediaFileName):
        """Add new media object (image, movie, etc...)
        """
        return self.__upload_file(mediaFileName)

    def upload_file(self, filename, overwrite=False):
        '''Same as newMediaObject, but passes WP-specific fields'''
        # FIXME: this doesn't seem to overwrite anything. Not sure why.
        return self.__upload_file(filename, type=mimetypes.guess_type(filename)[0],
                                  overwrite=overwrite)

    @wordpress_call
    def __upload_file(self, mediaFileName, **fields):
        f = file(mediaFileName, 'rb')
        mediaBits = f.read()
        f.close()

        mediaStruct = {
            'name' : os.path.basename(mediaFileName),
            'bits' : xmlrpc.client.Binary(mediaBits)
        }

        mediaStruct.update(fields)

        # N.B. wnp.uploadFile is alias for newMediaObject,
        # so it doesn't matter which one we call
        result = self._server.metaWeblog.newMediaObject(self.blogId,
                                self.user, self.password, mediaStruct)
        return result['url']

