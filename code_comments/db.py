# -*- coding: utf-8 -*-

from trac.core import Component, implements
from trac.db.schema import Table, Column, Index
from trac.env import IEnvironmentSetupParticipant
from trac.db.api import DatabaseManager

# Database version identifier for upgrades.
db_version = 3
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
        Index(['path']),
        Index(['author']),
    ],
    'code_comments_subscriptions': Table('code_comments_subscriptions',
                                         key=('id', 'user', 'type', 'path',
                                              'repos', 'rev'))[
        Column('id', auto_increment=True),
        Column('user'),
        Column('type'),
        Column('path'),
        Column('repos'),
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


upgrade_map = {
    2: upgrade_from_1_to_2,
    3: upgrade_from_2_to_3,
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
