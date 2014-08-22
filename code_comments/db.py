from trac.core import Component, implements
from trac.db.schema import Table, Column, Index
from trac.env import IEnvironmentSetupParticipant
from trac.db.api import DatabaseManager

# Database version identifier for upgrades.
db_version = 3

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


def to_sql(env, table):
    """ Convenience function to get the to_sql for the active connector."""
    dc = DatabaseManager(env)._get_connector()[0]
    return dc.to_sql(table)


def create_tables(env, db):
    cursor = db.cursor()
    for table_name in schema:
        for stmt in to_sql(env, schema[table_name]):
            cursor.execute(stmt)
    cursor.execute(
        "INSERT INTO system VALUES ('code_comments_schema_version', %s)",
        str(db_version))


# Upgrades

def upgrade_from_1_to_2(env, db):
    # Add the new column "type"
    @env.with_transaction()
    def add_type_column(db):
        cursor = db.cursor()
        cursor.execute('ALTER TABLE code_comments ADD COLUMN type TEXT')

    # Convert all the current comments to the new schema
    @env.with_transaction()
    def convert_comments(db):
        comments = {}
        cursor = db.cursor()
        cursor.execute('SELECT id, path FROM code_comments')
        comments = cursor.fetchall()
        # options:
        # 1: comment on file (path != "" && path != "attachment")
        # 2: comment on changeset (path == "")
        # 3: comment on attachment (path == "attachment")
        for comment in comments:
            path = comment[1]
            is_comment_to_attachment = path.startswith('attachment')
            is_comment_to_file = not is_comment_to_attachment and '' != path
            is_comment_to_changeset = '' == path
            cursor = db.cursor()
            update = 'UPDATE code_comments SET type={0} WHERE id={1}'
            sql = ''

            if is_comment_to_changeset:
                sql = update.format("'changeset'", str(comment[0]))
            elif is_comment_to_attachment:
                sql = update.format("'attachment'", str(comment[0]))
            elif is_comment_to_file:
                sql = update.format("'browser'", str(comment[0]))

            cursor.execute(sql)


def upgrade_from_2_to_3(env, db):
    # Add the new table
    @env.with_transaction()
    def add_subscriptions_table(db):
        cursor = db.cursor()
        for stmt in to_sql(env, schema['code_comments_subscriptions']):
            cursor.execute(stmt)


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

    def environment_needs_upgrade(self, db):
        """
        Called when Trac checks whether the environment needs to be upgraded.
        Returns `True` if upgrade is needed, `False` otherwise.
        """
        return self._get_version(db) != db_version

    def upgrade_environment(self, db):
        """
        Actually perform an environment upgrade, but don't commit as
        that is done by the common upgrade procedure when all plugins are done.
        """
        current_ver = self._get_version(db)
        if current_ver == 0:
            create_tables(self.env, db)
        else:
            while current_ver+1 <= db_version:
                upgrade_map[current_ver+1](self.env, db)
                current_ver += 1
            cursor = db.cursor()
            cursor.execute(
                "UPDATE system SET value=%s WHERE name='code_comments_schema_version'",
                str(db_version))

    def _get_version(self, db):
        cursor = db.cursor()
        try:
            sql = "SELECT value FROM system WHERE name='code_comments_schema_version'"
            cursor.execute(sql)
            for row in cursor:
                return int(row[0])
            return 0
        except:
            return 0
