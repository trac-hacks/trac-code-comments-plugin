from trac.core import *
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
        Column('revision'),
        Column('line', type='int'),
        Column('author'),
        Column('time', type='int'),
        Column('repository'),
        Index(['path']),
        Index(['author']),
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
    cursor.execute("INSERT into system values ('code_comments_schema_version', %s)",
                        str(db_version))
# Upgrades
def upgrade_from_1_to_2(env, db):
    columns = [c.name for c in schema['code_comments'].columns]
    cursor = db.cursor()
    values = cursor.execute('PRAGMA INDEX_LIST(`code_comments`)')
    indexes = values.fetchall()
    for index in indexes:
        if index[1].startswith('code_comments'):
            cursor.execute('DROP INDEX IF EXISTS %s' % index[1])
    values = cursor.execute('SELECT %s FROM code_comments' % ','.join(columns))
    lines = values.fetchall()
    cursor.execute('ALTER TABLE code_comments RENAME TO tmp_code_comments')
    for stmt in to_sql(env, schema['code_comments']):
        cursor.execute(stmt)
    for line in lines:
        ins = 'INSERT INTO code_comments (%s) VALUES (%s)' % (','.join(columns), ','.join(['\'%s\'' % str(v).replace('\'','\'\'') for v in line]))
        cursor.execute(ins)
    cursor.execute('DROP TABLE tmp_code_comments')

def upgrade_from_2_to_3(env, db):
    cursor = db.cursor()
    cursor.execute('ALTER TABLE code_comments ADD COLUMN repository text')

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
        """Called when Trac checks whether the environment needs to be upgraded.
        Returns `True` if upgrade is needed, `False` otherwise."""
        return self._get_version(db) != db_version

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade, but don't commit as
        that is done by the common upgrade procedure when all plugins are done."""
        current_ver = self._get_version(db)
        if current_ver == 0:
            create_tables(self.env, db)
        else:
            while current_ver+1 <= db_version:
                upgrade_map[current_ver+1](self.env, db)
                current_ver += 1
            cursor = db.cursor()
            cursor.execute("UPDATE system SET value=%s WHERE name='code_comments_schema_version'",
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
