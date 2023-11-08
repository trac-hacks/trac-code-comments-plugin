# -*- coding: utf-8 -*-

from trac.core import Component, implements
from trac.db.schema import Table, Column, Index
from trac.env import IEnvironmentSetupParticipant
from trac.db.api import DatabaseManager
from trac.versioncontrol.api import RepositoryManager

# Database version identifier for upgrades.
db_version = 5
db_version_key = 'code_comments_schema_version'

# Database schema
schema = {
    'code_comments': Table('code_comments', key=('id', 'version'))[
        Column('id', auto_increment=True),
        Column('version', type='int'),
        Column('text'),
        Column('path'),
        Column('revision', type='int'),
        Column('line', type='int'),
        Column('author'),
        Column('time', type='int'),
        Column('type'),
        Column('reponame'),
        Index(['path']),
        Index(['author']),
        Index(['reponame', 'path']),
        Index(['revision', 'reponame']),
    ],
    'code_comments_subscriptions': Table('code_comments_subscriptions',
                                         key=('id', 'user', 'type', 'path',
                                              'repos', 'rev'))[
        Column('id', auto_increment=True),
        Column('user'),
        Column('type'),
        Column('path'),
        Column('rev'),
        Column('notify', type='bool'),
        Index(['user']),
        Index(['path']),
    ],
}


# Upgrades

def upgrade_from_1_to_2(env):
    with env.db_transaction as db:
        # Add the new column "type"
        db('ALTER TABLE code_comments ADD COLUMN type TEXT')
        # Convert all the current comments to the new schema
        # options:
        # 1: comment on file (path != "" && path != "attachment")
        # 2: comment on changeset (path == "")
        # 3: comment on attachment (path == "attachment")
        for comment in db("""
                SELECT id, path FROM code_comments
                """):
            path = comment[1]
            is_comment_to_attachment = path.startswith('attachment')
            is_comment_to_file = not is_comment_to_attachment and '' != path
            is_comment_to_changeset = '' == path
            update = 'UPDATE code_comments SET type={0} WHERE id={1}'
            sql = ''

            if is_comment_to_changeset:
                sql = update.format("'changeset'", str(comment[0]))
            elif is_comment_to_attachment:
                sql = update.format("'attachment'", str(comment[0]))
            elif is_comment_to_file:
                sql = update.format("'browser'", str(comment[0]))

            db(sql)


def upgrade_from_2_to_3(env):
    # Add the new table
    dbm = DatabaseManager(env)
    dbm.create_tables((schema['code_comments_subscriptions'],))


def upgrade_from_3_to_4(env):
    with env.db_transaction as db:
        # Add the new column "reponame" and indexes.
        db('ALTER TABLE code_comments ADD COLUMN reponame text')
        db('CREATE INDEX code_comments_reponame_path_idx ON code_comments (reponame, path)')
        db('CREATE INDEX code_comments_revision_reponame_idx ON code_comments (revision, reponame)')

        # Comments on attachments need to have the empty string as the reponame instead of NULL.
        db("UPDATE code_comments SET reponame = '' WHERE type = 'attachment'")

        # Comments on changesets have the reponame in the 'path' column.
        db("UPDATE code_comments SET reponame = path, path = '' WHERE type = 'changeset'")

        # Comments on files have the reponame as the first component of the 'path' column.
        db("""
            UPDATE code_comments
            SET
                reponame = substr(path, 1, instr(path, '/') - 1),
                path = substr(path, instr(path, '/') + 1)
            WHERE
                type = 'browser'
            """)


def upgrade_from_4_to_5(env):
    with env.db_transaction as db:
        # The line numbers of all present comments on changesets are bogus,
        # see https://github.com/trac-hacks/trac-code-comments-plugin/issues/67
        # We therefore set them to 0 detaching the comment from the line. We leave a note in
        # the text of the comment explaining this.

        notice = '\n\nThis comment was created by a previous version of the '\
                 "code-comments plugin and '''is not properly attached to a line of code'''. "\
                 'See [https://github.com/trac-hacks/trac-code-comments-plugin/issues/67 '\
                 'issue #67].\n\nThe comment was originally placed on line $oldLineNumber$ of '\
                 'the diff as it was displayed when the comment was created.'
        notice = notice.replace("'", "''")
        sql = """
            UPDATE code_comments
            SET
                line = 0,
                text = text || REPLACE('{0}', '$oldLineNumber$', line)
            WHERE
                type = 'changeset'
                AND
                line != 0
            """
        db(sql.format(notice))


upgrade_map = {
    2: upgrade_from_1_to_2,
    3: upgrade_from_2_to_3,
    4: upgrade_from_3_to_4,
    5: upgrade_from_4_to_5
}


class CodeCommentsSetup(Component):
    """Component that deals with database setup and upgrades."""

    implements(IEnvironmentSetupParticipant)

    def environment_created(self):
        """Called when a new Trac environment is created."""
        pass

    def environment_needs_upgrade(self):
        """
        Called when Trac checks whether the environment needs to be upgraded.
        Returns `True` if upgrade is needed, `False` otherwise.
        """
        dbm = DatabaseManager(self.env)
        return dbm.get_database_version(db_version_key) != db_version

    def upgrade_environment(self):
        """
        Actually perform an environment upgrade, but don't commit as
        that is done by the common upgrade procedure when all plugins are done.
        """
        dbm = DatabaseManager(self.env)
        current_ver = dbm.get_database_version(db_version_key)
        if current_ver == 0:
            dbm.create_tables(schema.values())
        else:
            while current_ver + 1 <= db_version:
                upgrade_map[current_ver + 1](self.env)
                current_ver += 1
        dbm.set_database_version(db_version, db_version_key)
