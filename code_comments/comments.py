from trac.wiki.formatter import format_to_html
from trac.mimeview.api import Context
from trac.util.datefmt import format_datetime
from time import gmtime, strftime
from code_comments import db
from trac.util import Markup

try:
    import json
except ImportError:
    import simplejson as json

class Comment:
    columns = [column.name for column in db.schema['code_comments'].columns]

    def __init__(self, req, env, row):
        self.__dict__ = dict(zip(self.columns, row))
        self.env = env
        self.req = req
        context = Context.from_request(self.req, 'wiki')
        self.html = format_to_html(self.env, context, self.text)

    def href(self):
        #TODO: if the user doesn't have permissions, don't add the codecomment argument
        if self.path:
            return self.req.href.browser(None, self.path, rev=self.revision, codecomment=self.id) + '#L' + str(self.line)
        else:
            return self.req.href.changeset(self.revision, codecomment=self.id)

    def path_revision_line(self):
        line_suffix = ''
        if self.line:
            line_suffix = '#L'+str(self.line)
        return '%s@%s%s' % (self.path, self.revision, line_suffix) 

    def trac_link(self):
        return 'source:' + self.path_revision_line()

    def path_link_tag(self):
        return Markup('<a href="%s">%s</a>' % (self.href(), self.path_revision_line()))

    def formatted_time(self):
        return strftime('%b, %d %Y %H:%M:%S', gmtime(self.time))

    def delete(self):
        @self.env.with_transaction()
        def delete_comment(db):
            cursor = db.cursor()
            cursor.execute("DELETE FROM code_comments WHERE id=%s", [self.id])

class CommentJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Comment):
            for_json = dict(((column, getattr(o, column)) for column in o.columns))
            for_json['formatted_date'] = o.formatted_time()
            for_json['permalink'] = o.href()
            for_json['html'] = o.html
            return for_json
        else:
            return json.JSONEncoder.default(self, o)

class Comments:
    def __init__(self, req, env):
        self.req, self.env = req, env

    def comment_from_row(self, row):
        return Comment(self.req, self.env, row)

    def select(self, *query):
        result = {}
        @self.env.with_transaction()
        def get_comments(db):
            cursor = db.cursor()
            cursor.execute(*query)
            result['comments'] = cursor.fetchall()
        return [self.comment_from_row(row) for row in result['comments']]

    def all(self):
        return self.select("SELECT * FROM code_comments ORDER BY time DESC")

    def by_id(self, id):
        return self.select("SELECT * FROM code_comments WHERE id=%s ORDER BY time DESC", [id])[0]

    def search(self, args):
        conditions = ' AND '.join(['%s=%%s' % name for name in args.keys()])
        where = ''
        if conditions:
            where = 'WHERE '+conditions
        return self.select('SELECT * FROM code_comments ' + where + ' ORDER BY time DESC', args.values())
