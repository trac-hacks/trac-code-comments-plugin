from trac.wiki.formatter import format_to_html
from trac.mimeview.api import Context
from trac.util.datefmt import format_datetime
from time import gmtime, strftime
from vip import db
from trac.util import Markup

class Comment:
    columns = [column.name for column in db.schema['vip_comments'].columns]
    
    def __init__(self, req, env, row):
        self.__dict__ = dict(zip(self.columns, row))
        self.env = env
        self.req = req
        context = Context.from_request(self.req, 'wiki')
        self.html = format_to_html(self.env, context, self.text)
    
    def href(self):
        #TODO: if the user doesn't have permissions, don't add the codecomment argument
        return self.req.href.browser(None, self.path, rev=self.revision, codecomment=self.id) + '#L' + str(self.line)
    
    def path_revision_line(self):
        return '%s@%s%s' % (self.path, self.revision, '#L'+str(self.line) if self.line else '')        
    
    def trac_link(self):
        return 'source:' + self.path_revision_line()
    
    def path_link_tag(self):
        return Markup('<a href="%s">%s</a>' % (self.href(), self.path_revision_line()))
    
    def formatted_time(self):
        return strftime('%b, %d %Y %H:%M:%S', gmtime(self.time))
    
        

class Comments:
    def __init__(self, req, env):
        self.req, self.env = req, env

    def comment_from_row(self, row):
        return Comment(self.req, self.env, row)

    def query(self, *query):
        result = {}
        @self.env.with_transaction()
        def get_comments(db):
            cursor = db.cursor()
            cursor.execute(*query)
            result['comments'] = cursor.fetchall()
        return [self.comment_from_row(row) for row in result['comments']]

    def all(self):
        return self.query("SELECT * FROM vip_comments ORDER BY time DESC")
    
    def by_id(self, id):
        return self.query("SELECT * FROM vip_comments WHERE id=%s ORDER BY time DESC", [id])[0]
