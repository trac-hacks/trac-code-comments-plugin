from trac.admin import IAdminCommandProvider
from trac.attachment import Attachment, IAttachmentChangeListener
from trac.core import Component, implements
from trac.versioncontrol import (
    RepositoryManager, NoSuchChangeset, IRepositoryChangeListener)

from code_comments.api import ICodeCommentChangeListener
from code_comments.comments import Comments


class Subscription(object):
    """
    Representation of a code comment subscription.
    """
    id = 0
    user = ''
    role = ''
    type = ''
    path = ''
    rev = ''
    repos = ''
    notify = 'always'

    def __init__(self, env, data=None):
        if isinstance(data, dict):
            self.__dict__ = data
        self.env = env

    @classmethod
    def select(cls, env, args={}):
        select = 'SELECT * FROM code_comments_subscriptions'
        if len(args) > 0:
            select += ' WHERE '
            criteria = []
            for key, value in args.iteritems():
                template = '{0}={1}'
                if isinstance(value, str):
                    template = '{0}=\'{1}\''
                criteria.append(template.format(key, value))
            select += ' AND '.join(criteria)
        cursor = env.get_read_db().cursor()
        cursor.execute(select)
        for row in cursor:
            yield cls._from_row(env, row)

    def insert(self, db=None):
        """
        Insert a new subscription. Returns bool to indicate success.
        """
        if self.id > 0:
            # Already has an id, don't insert
            return False
        else:
            @self.env.with_transaction()
            def do_insert(db):
                cursor = db.cursor()
                insert = ("INSERT INTO code_comments_subscriptions "
                          "(user, role, type, path, repos, rev, notify) "
                          "VALUES (%s, %s, %s, %s, %s, %s, %s)")
                values = (self.user, self.role, self.type, self.path,
                          self.repos, self.rev, self.notify)
                cursor.execute(insert, values)
                self.id = db.get_last_id(cursor, 'code_comments_subscriptions')
                return True

    def update(self, db=None):
        """
        Update an existing subscription. Returns bool to indicate success.
        """
        if self.id == 0:
            # Doesn't have a valid id, don't update
            return False
        else:
            @self.env.with_transaction()
            def do_update(db):
                cursor = db.cursor()
                update = ("UPDATE code_comments_subscriptions SET "
                          "user=%s, role=%s, type=%s, path=%s, repos=%s, "
                          "rev=%s, notify=%s WHERE id=%s")
                values = (self.user, self.role, self.type, self.path,
                          self.repos, self.rev, self.notify, self.id)
                try:
                    cursor.execute(update, values)
                except db.IntegrityError:
                    self.env.log.warning("Subscription update failed.")
                    return False
                return True

    def delete(self, db=None):
        """
        Delete an existing subscription.
        """
        if self.id > 0:
            @self.env.with_transaction()
            def do_delete(db):
                cursor = db.cursor()
                delete = ("DELETE FROM code_comments_subscriptions WHERE "
                          "id=%s")
                cursor.execute(delete, (self.id,))

    @classmethod
    def _from_row(cls, env, row):
        """
        Creates a subscription from a list (representing a database row).
        """
        try:
            subscription = cls(env)
            subscription.id = int(row[0])
            subscription.user = row[1]
            subscription.role = row[2]
            subscription.type = row[3]
            subscription.path = row[4]
            subscription.repos = row[5]
            subscription.rev = row[6]
            subscription.notify = row[7]
            return subscription
        except IndexError:
            # Invalid row
            return None

    @classmethod
    def _from_dict(cls, env, dict_):
        """
        Creates a subscription from a dict.
        """
        cursor = env.get_read_db().cursor()
        select = ("SELECT * FROM code_comments_subscriptions WHERE "
                  "user=%s AND type=%s AND path=%s AND "
                  "repos=%s AND rev=%s AND notify=%s"
                  )
        values = (dict_['user'], dict_['type'], dict_['path'], dict_['repos'],
                  dict_['rev'], dict_['notify'])
        cursor.execute(select, values)
        row = cursor.fetchone()
        if row:
            env.log.debug(
                'Subscription for {type} already exists'.format(**dict_))
            return cls._from_row(env, row)
        else:
            env.log.debug(
                'Subscription for {type} created'.format(**dict_))
            subscription = cls(env, dict_)
            subscription.insert()
            return subscription

    @classmethod
    def from_attachment(cls, env, attachment, user=None, role='author',
                        notify='always'):
        """
        Creates a subscription from an Attachment object.
        """
        _path = "/{0}/{1}/{2}".format(attachment.parent_realm,
                                      attachment.parent_id,
                                      attachment.filename)

        sub = {
            'user': user or attachment.author,
            'role': role,
            'type': 'attachment',
            'path': _path,
            'repos': '',
            'rev': '',
            'notify': notify,
        }
        return cls._from_dict(env, sub)

    @classmethod
    def from_changeset(cls, env, changeset, user=None, role='author',
                       notify='always'):
        """
        Creates a subscription from a Changeset object.
        """
        sub = {
            'user': user or changeset.author,
            'role': role,
            'type': 'changeset',
            'path': '',
            'repos': changeset.repos.reponame,
            'rev': changeset.rev,
            'notify': notify,
        }
        return cls._from_dict(env, sub)

    @classmethod
    def from_comment(cls, env, comment, user=None, role='commenter',
                     notify='always'):
        """
        Creates a subscription from a Comment object.
        """
        sub = {
            'user': user or comment.author,
            'role': user,
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
            if comment.type == 'browser':
                sub['path'] = comment.path
            else:
                sub['path'] = ''
            repo = RepositoryManager(env).get_repository(None)
            try:
                sub['repos'] = repo.reponame
                try:
                    _cs = repo.get_changeset(comment.revision)
                    sub['rev'] = _cs.rev
                except NoSuchChangeset:
                    # Invalid changeset
                    return None
            finally:
                repo.close()

        return cls._from_dict(env, sub)

    @classmethod
    def for_attachment(cls, env, attachment, path=None):
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
        return cls.select(env, args)

    @classmethod
    def for_changeset(cls, env, changeset):
        """
        Returns all subscriptions for an changeset.
        """
        args = {
            'type': 'changeset',
            'repos': changeset.repos.reponame,
            'rev': changeset.rev,
        }
        return cls.select(env, args)


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
        cursor = self.env.get_read_db().cursor()
        cursor.execute("SELECT DISTINCT type, id FROM attachment")
        rows = cursor.fetchall()
        for row in rows:
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
        # Handle existing subscriptions
        if changeset.author != old_changeset.author:
            for subscription in Subscription.for_changeset(self.env,
                                                           changeset):
                if (subscription.user == old_changeset.author and
                        subscription.role == 'author'):
                    subscription.role = 'subscriber'

                if subscription.user == changeset.author:
                    subscription.role = 'author'

                subscription.update()

        # Create a new author subscription
        Subscription.from_changeset(self.env, changeset)

    # ICodeCommentChangeListener methods

    def comment_created(self, comment):
        Subscription.from_comment(self.env, comment)
