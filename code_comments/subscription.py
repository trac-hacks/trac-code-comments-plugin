# -*- coding: utf-8 -*-

import json
import re

from trac.admin import IAdminCommandProvider
from trac.attachment import Attachment, IAttachmentChangeListener
from trac.core import Component, implements
from trac.util.html import html as tag
from trac.versioncontrol import (
    RepositoryManager, NoSuchChangeset, IRepositoryChangeListener)
from trac.web.api import HTTPNotFound, IRequestHandler, ITemplateStreamFilter

from genshi.filters import Transformer

from code_comments.api import ICodeCommentChangeListener
from code_comments.comments import Comments


class Subscription(object):
    """
    Representation of a code comment subscription.
    """

    id = 0
    user = ''
    type = ''
    path = ''
    rev = ''
    repos = ''
    notify = True

    def __init__(self, env, data=None):
        if isinstance(data, dict):
            self.__dict__ = data
        self.env = env

    def __str__(self):
        """
        Returns a user friendly string representation.
        """
        template = "{0} for {1} {2}"
        if self.type == "changeset":
            _identifier = self.rev
        elif self.type == "browser":
            _identifier = "{0} @ {1}".format(self.path, self.rev)
        else:
            _identifier = self.path

        return template.format(self.user, self.type, _identifier)

    @classmethod
    def select(cls, env, args={}, notify=None):
        """
        Retrieve existing subscription(s).
        """
        select = u'SELECT * FROM code_comments_subscriptions'

        if notify:
            args['notify'] = bool(notify)

        if len(args) > 0:
            select += ' WHERE '
            criteria = []
            for key, value in args.iteritems():
                template = u'{0}={1}'
                if isinstance(value, basestring):
                    template = u'{0}=\'{1}\''
                if (isinstance(value, tuple) or isinstance(value, list)):
                    template = u'{0} IN (\'{1}\')'
                    value = u'\',\''.join(value)
                if isinstance(value, bool):
                    value = int(value)
                criteria.append(template.format(key, value))
            select += u' AND '.join(criteria)

        for row in env.db_query(select):
            yield cls._from_row(env, row)

    def insert(self):
        """
        Insert a new subscription. Returns bool to indicate success.
        """
        if self.id > 0:
            # Already has an id, don't insert
            return False
        else:
            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO code_comments_subscriptions
                     (user, type, path, repos, rev, notify)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """, (self.user, self.type, self.path, self.repos,
                          self.rev, self.notify))
                self.id = db.get_last_id(cursor, 'code_comments_subscriptions')
                return True

    def update(self):
        """
        Update an existing subscription. Returns bool to indicate success.
        """
        if self.id == 0:
            # Doesn't have a valid id, don't update
            return False
        else:
            try:
                self.env.db_transaction("""
                    UPDATE code_comments_subscriptions
                    SET user=%s, type=%s, path=%s, repos=%s, rev=%s,
                        notify=%s WHERE id=%s
                    """, (self.user, self.type, self.path, self.repos,
                          self.rev, self.notify, self.id))
            except self.env.db_exc.IntegrityError:
                self.env.log.warning("Subscription update failed.")
                return False
            return True

    def delete(self):
        """
        Delete an existing subscription.
        """
        if self.id > 0:
            self.env.db_transaction("""
                DELETE FROM code_comments_subscriptions WHERE id=%s
                """, (self.id,))

    @classmethod
    def _from_row(cls, env, row):
        """
        Creates a subscription from a list (representing a database row).
        """
        try:
            subscription = cls(env)
            subscription.id = int(row[0])
            subscription.user = row[1]
            subscription.type = row[2]
            subscription.path = row[3]
            subscription.repos = row[4]
            subscription.rev = row[5]
            subscription.notify = bool(row[6])
            return subscription
        except IndexError:
            # Invalid row
            return None

    @classmethod
    def from_dict(cls, env, dict_, create=True):
        """
        Retrieves or (optionally) creates a subscription from a dict.
        """
        subscription = None

        # Look for existing subscriptions
        args = {
            'user': dict_['user'],
            'type': dict_['type'],
            'path': dict_['path'],
            'repos': dict_['repos'],
            'rev': dict_['rev'],
        }
        subscriptions = cls.select(env, args)

        # Only return the first one
        for _subscription in subscriptions:
            if subscription is None:
                subscription = _subscription
                env.log.info('Subscription found: [%d] %s',
                             subscription.id, subscription)
            else:
                # The unique constraint on the table should prevent this ever
                # occurring
                env.log.warning('Multiple subscriptions found: [%d] %s',
                                subscription.id, subscription)

        # (Optionally) create a new subscription if we didn't find one
        if subscription is None:
            subscription = cls(env, dict_)
            if create:
                subscription.insert()
                env.log.info('Subscription created: [%d] %s',
                             subscription.id, subscription)

        return subscription

    @classmethod
    def from_attachment(cls, env, attachment, user=None, notify=True):
        """
        Creates a subscription from an Attachment object.
        """
        _path = u"/{0}/{1}/{2}".format(attachment.parent_realm,
                                      attachment.parent_id,
                                      attachment.filename)

        sub = {
            'user': user or attachment.author,
            'type': 'attachment',
            'path': _path,
            'repos': '',
            'rev': '',
            'notify': notify,
        }
        return cls.from_dict(env, sub)

    @classmethod
    def from_changeset(cls, env, changeset, user=None, notify=True):
        """
        Creates a subscription from a Changeset object.
        """
        sub = {
            'user': user or changeset.author,
            'type': 'changeset',
            'path': '',
            'repos': changeset.repos.reponame,
            'rev': changeset.rev,
            'notify': notify,
        }
        return cls.from_dict(env, sub)

    @classmethod
    def from_comment(cls, env, comment, user=None, notify=True):
        """
        Creates a subscription from a Comment object.
        """
        sub = {
            'user': user or comment.author,
            'type': comment.type,
            'notify': notify,
        }

        # Munge attachments
        if comment.type == 'attachment':
            sub['path'] = comment.path.split(':')[1]
            sub['repos'] = ''
            sub['rev'] = ''

        # Munge changesets and browser
        if comment.type in ('changeset', 'browser'):
            rm = RepositoryManager(env)
            reponame, repos, path = rm.get_repository_by_path(comment.path)
            if comment.type == 'browser':
                sub['path'] = path
            else:
                sub['path'] = ''
            sub['repos'] = reponame or '(default)'
            try:
                _cs = repos.get_changeset(comment.revision)
            except NoSuchChangeset:
                # Invalid changeset
                return None
            else:
                sub['rev'] = _cs.rev

        return cls.from_dict(env, sub)

    @classmethod
    def for_attachment(cls, env, attachment, path=None, notify=None):
        """
        Returns all subscriptions for an attachment. The path can be
        overridden.
        """
        path_template = "/{0}/{1}/{2}"
        _path = path or path_template.format(attachment.parent_realm,
                                             attachment.parent_id,
                                             attachment.filename)
        args = {
            'type': 'attachment',
            'path': _path,
        }
        return cls.select(env, args, notify)

    @classmethod
    def for_changeset(cls, env, changeset, notify=None):
        """
        Returns all subscriptions for an changeset.
        """
        args = {
            'type': 'changeset',
            'repos': changeset.repos.reponame,
            'rev': changeset.rev,
        }
        return cls.select(env, args, notify)

    @classmethod
    def for_comment(cls, env, comment, notify=None):
        """
        Return all subscriptions for a comment.
        """
        args = {}
        if comment.type == 'attachment':
            args['type'] = comment.type
            args['path'] = comment.path.split(':')[1]

        if comment.type == 'changeset':
            args['type'] = comment.type
            args['rev'] = str(comment.revision)

        if comment.type == 'browser':
            rm = RepositoryManager(env)
            reponame, _, path = rm.get_repository_by_path(comment.path)
            args['type'] = ('browser', 'changeset')
            args['path'] = (path, '')
            args['repos'] = reponame
            args['rev'] = (str(comment.revision), '')

        return cls.select(env, args, notify)

    @classmethod
    def for_request(cls, env, req, create=False):
        """
        Return a **single** subscription for a HTTP request.
        """
        rm = RepositoryManager(env)

        dict_ = {
            'user': req.authname,
            'type': req.args.get('realm'),
            'path': '',
            'rev': '',
            'repos': '',
        }
        path = req.args.get('path') or ''

        if dict_['type'] == 'attachment':
            dict_['path'] = path

        if dict_['type'] == 'changeset':
            parts = [p for p in path.split('/') if p]
            dict_['rev'] = parts[0]
            dict_['repos'] = parts[1]

        if dict_['type'] == 'browser':
            reponame, repos, path = rm.get_repository_by_path(path)
            dict_['path'] = '/' if len(path) == 0 else path
            dict_['rev'] = req.args.get('rev') or ''
            dict_['repos'] = reponame

        return cls.from_dict(env, dict_, create=create)


class SubscriptionJSONEncoder(json.JSONEncoder):
    """
    JSON Encoder for a Subscription object.
    """
    def default(self, o):
        data = o.__dict__.copy()
        del data['env']
        return data


class SubscriptionAdmin(Component):
    """
    trac-admin command provider for subscription administration.
    """
    implements(IAdminCommandProvider)

    # IAdminCommandProvider methods

    def get_admin_commands(self):
        yield ('subscription seed', '',
               """Seeds subscriptions for existing attachments, changesets,
               and comments.
               """,
               None, self._do_seed)

    def _do_seed(self):
        # Create a subscription for all existing attachments
        for row in self.env.db_query("""
                SELECT DISTINCT type, id FROM attachment
                """):
            for attachment in Attachment.select(self.env, row[0], row[1]):
                Subscription.from_attachment(self.env, attachment)

        # Create a subscription for all existing revisions
        rm = RepositoryManager(self.env)
        repos = rm.get_real_repositories()
        for repo in repos:
            _rev = repo.get_oldest_rev()
            while _rev:
                try:
                    _cs = repo.get_changeset(_rev)
                    Subscription.from_changeset(self.env, _cs)
                except NoSuchChangeset:
                    pass
                _rev = repo.next_rev(_rev)

        # Create a subscription for all existing comments
        comments = Comments(None, self.env).all()
        for comment in comments:
            Subscription.from_comment(self.env, comment)


class SubscriptionListeners(Component):
    """
    Automatically creates subscriptions for attachments, changesets, and
    comments.
    """
    implements(IAttachmentChangeListener, IRepositoryChangeListener,
               ICodeCommentChangeListener)

    # IAttachmentChangeListener methods

    def attachment_added(self, attachment):
        Subscription.from_attachment(self.env, attachment)

    def attachment_deleted(self, attachment):
        for subscription in Subscription.for_attachment(self.env, attachment):
            subscription.delete()

    def attachment_reparented(self, attachment, old_parent_realm,
                              old_parent_id):
        path_template = "/{0}/{1}/{2}"
        old_path = path_template.format(old_parent_realm,
                                        old_parent_id,
                                        attachment.filename)
        new_path = path_template.format(attachment.parent_realm,
                                        attachment.parent_id,
                                        attachment.filename)

        for subscription in Subscription.for_attachment(self.env, attachment,
                                                        old_path):
            subscription.path = new_path
            subscription.update()

    # IRepositoryChangeListener methods

    def changeset_added(self, repos, changeset):
        Subscription.from_changeset(self.env, changeset)

    def changeset_modified(self, repos, changeset, old_changeset):
        if changeset.author != old_changeset.author:
            # Create a new author subscription
            Subscription.from_changeset(self.env, changeset)

    # ICodeCommentChangeListener methods

    def comment_created(self, comment):
        Subscription.from_comment(self.env, comment)


class SubscriptionModule(Component):
    implements(IRequestHandler, ITemplateStreamFilter)

    # IRequestHandler methods

    def match_request(self, req):
        match = re.match(r'\/subscription\/(\w+)(\/?.*)$', req.path_info)
        if match:
            if match.group(1):
                req.args['realm'] = match.group(1)
            if match.group(2):
                req.args['path'] = match.group(2)
            return True

    def process_request(self, req):
        if req.method == 'POST':
            return self._do_POST(req)
        elif req.method == 'PUT':
            return self._do_PUT(req)
        return self._do_GET(req)

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        if re.match(r'^/(changeset|browser|attachment/ticket/\d+/.?).*',
                    req.path_info):
            filter = Transformer('//h1')
            button = self._subscription_button(req.path_info,
                                               req.args.get('rev'))
            stream |= filter.before(button)
        return stream

    # Internal methods

    def _do_GET(self, req):
        subscription = Subscription.for_request(self.env, req)
        if subscription is None:
            req.send('', 'application/json', 204)
        req.send(json.dumps(subscription, cls=SubscriptionJSONEncoder),
                 'application/json')

    def _do_POST(self, req):
        content = req.read()
        data = json.loads(content)
        subscription = Subscription.from_dict(self.env, data, create=True)
        status = 201
        req.send(json.dumps(subscription, cls=SubscriptionJSONEncoder),
                 'application/json', status)

    def _do_PUT(self, req):
        content = req.read()
        if len(content) > 0:
            data = json.loads(content)
            subscription = Subscription.from_dict(self.env, data, create=True)
            subscription.notify = data['notify']
            subscription.update()
        req.send(json.dumps(subscription, cls=SubscriptionJSONEncoder),
                 'application/json')

    def _subscription_button(self, path, rev):
        """
        Generates a (disabled) button to connect JavaScript to.
        """
        return tag.button(
            'Subscribe', id_='subscribe', disabled=True,
            title=('Code comment subscriptions require JavaScript '
                   'to be enabled'),
            data_base_url=self.env.project_url or self.env.abs_href(),
            data_path=path,
            data_rev=rev)
