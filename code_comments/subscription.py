from trac.admin import IAdminCommandProvider
from trac.core import Component, implements
from trac.versioncontrol import RepositoryManager, NoSuchChangeset

from code_comments.comments import Comments


def create_subscription(env, user, role, type_, path, rev, repos=None,
                        notify='always'):
    """
    Create a code comment subscription for a given user.

    :param str user: The user to subscribe
    :param str role: The type of subscription: "author" or "commenter"
    :param str_ type: What the subscription is to e.g., "attachment"
    :param path: The path of the subscription
    :type path: str or None
    :param repos: The name of repository
    :type repos: str or None
    :param rev: The revision
    :type repos: int or None
    :param str notify: Whether the subscription issues a notification
                    ("always") or not ("never")
    :return: The id of the new subscription
    :rtype: int
    """
    sub = {
        'user': user,
        'role': role,
        'type': type_,
        'path': path or '',
        'notify': notify,
    }

    if type_ in ('changeset', 'browser'):
        _repo = RepositoryManager(env).get_repository(repos)
        try:
            sub['repos'] = _repo.reponame
            if rev:
                sub['rev'] = _repo.db_rev(rev)
            else:
                sub['rev'] = 'any'  # wildcard
        finally:
            _repo.close()
    else:
        sub['repos'] = ''
        sub['rev'] = ''

    @env.with_transaction()
    def insert_subscription(db):
        cursor = db.cursor()
        select = ("SELECT id FROM code_comments_subscriptions WHERE "
                  "user = '{user}' AND type = '{type}' AND "
                  "path = '{path}' AND repos = '{repos}' AND "
                  "rev = '{rev}' AND notify = '{notify}'").format(**sub)
        cursor.execute(select)
        subs = cursor.fetchall()
        if len(subs) > 0:
            # There shouldn't really ever be more than one result
            env.log.debug(
                'Subscription for {type} already exists'.format(**sub))
            return subs[0]
        else:
            fields = ', '.join(sub.keys())
            values_template = ', '.join(['%s'] * len(sub))
            insert = ("INSERT INTO code_comments_subscriptions "
                      "({0}) VALUES ({1})").format(fields, values_template)
            cursor.execute(insert, sub.values())
            env.log.debug(
                'Subscription for {type} created'.format(**sub))
            return db.get_last_id(cursor, 'code_comments_subscriptions')


def create_subscription_from_changeset(env, changeset):
    sub = {
        'user': changeset.author,
        'role': 'author',
        'type_': 'changeset',
        'path': None,
        'repos': changeset.repos.reponame,
        'rev': changeset.rev,
        'notify': 'always',
    }
    create_subscription(env, **sub)


def create_subscription_from_comment(env, comment):
    sub = {
        'user': comment.author,
        'role': 'commenter',
        'type_': comment.type,
        'notify': 'always'
    }

    # Munge attachments
    if comment.type == 'attachment':
        sub['path'] = comment.path.split(':')[1]
        sub['repos'] = None,
        sub['rev'] = None

    # Munge changesets and browser
    if comment.type in ('changeset', 'browser'):
        if comment.type == 'browser':
            sub['path'] = comment.path
        else:
            sub['path'] = None
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

    return create_subscription(env, **sub)


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
                'type_': 'attachment',
                'path': "/{0}/{1}/{2}".format(*attachment),
                'repos': None,
                'rev': None,
                'notify': 'always',
            }
            create_subscription(self.env, **sub)

        # Create a subscription for all existing revisions
        rm = RepositoryManager(self.env)
        repos = rm.get_real_repositories()
        for repo in repos:
            _rev = repo.get_oldest_rev()
            while _rev:
                try:
                    _cs = repo.get_changeset(_rev)
                    create_subscription_from_changeset(self.env, _cs)
                except NoSuchChangeset:
                    pass
                _rev = repo.next_rev(_rev)

        # Create a subscription for all existing comments
        comments = Comments(None, self.env).all()
        for comment in comments:
            create_subscription_from_comment(self.env, comment)
