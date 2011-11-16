from trac.wiki.formatter import format_to_html
from trac.mimeview.api import Context
from vip import db

class Comment:
    columns = [column.name for column in db.schema['vip_comments'].columns]
    
    def __init__(self, req, env, row):
        self.__dict__ = dict(zip(self.columns, row))
        self.env = env
        self.req = req
        context = Context.from_request(req, 'wiki')
        self.html = format_to_html(self.env, context, self.text)


class Comments:
    def __init__(self, req, env):
        self.req, self.env = req, env

    def comment_from_row(self, row):
        return Comment(self.req, self.env, row)

    def query(self, query):
        result = {}
        @self.env.with_transaction()
        def get_comments(db):
            cursor = db.cursor()
            cursor.execute(query)
            result['comments'] = cursor.fetchall()
        return [self.comment_from_row(row) for row in result['comments']]

    def all(self):
        return self.query("SELECT * FROM vip_comments")