from trac.admin import IAdminCommandProvider
from trac.core import Component, implements
from trac.versioncontrol import RepositoryManager, NoSuchChangeset

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

    def insert(self, db=None):
        """
        Insert a new subscription.
        """
        @self.env.with_transaction(db)
        def do_insert(db):
            cursor = db.cursor()
            insert = ("INSERT INTO code_comments_subscriptions "
                      "(user, role, type, path, repos, rev, notify) "
                      "VALUES (%s, %s, %s, %s, %s, %s, %s)")
            values = (self.user, self.role, self.type, self.path, self.repos,
                      self.rev, self.notify)
            cursor.execute(insert, values)
            self.id = db.get_last_id(cursor, 'code_comments_subscriptions')

    @classmethod
    def _from_row(cls, env, row):
        """
        Creates a subscription from a list (representing a database row).
        """
        try:
            subscription = cls(env)
            subscription.id = row[0]
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
    def from_changeset(cls, env, changeset):
        """
        Creates a subscription from a Changeset object.
        """
        sub = {
            'user': changeset.author,
            'role': 'author',
            'type': 'changeset',
            'path': '',
            'repos': changeset.repos.reponame,
            'rev': changeset.rev,
            'notify': 'always',
        }
        return cls._from_dict(env, sub)

    @classmethod
    def from_comment(cls, env, comment):
        """
        Creates a subscription from a Comment object.
        """
        sub = {
            'user': comment.author,
            'role': 'commenter',
            'type': comment.type,
            'notify': 'always'
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
        cursor.execute("SELECT type, id, filename, author FROM attachment")
        attachments = cursor.fetchall()
        for attachment in attachments:
            sub = {
                'user': attachment[3],
                'role': 'author',
                'type': 'attachment',
                'path': "/{0}/{1}/{2}".format(*attachment),
                'repos': '',
                'rev': '',
                'notify': 'always',
            }
            Subscription._from_dict(self.env, sub)

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
