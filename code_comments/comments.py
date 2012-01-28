import trac.wiki.formatter
from time import time
from trac.mimeview.api import Context
from trac.util.datefmt import format_datetime
from time import gmtime, strftime
from code_comments import db
from trac.util import Markup

import re
import os.path

try:
    import json
except ImportError:
    import simplejson as json

try:
    import hashlib
    md5_hexdigest = lambda s: hashlib.md5(s).hexdigest()
except ImportError:
    import md5
    md5_hexdigest = lambda s: md5.new(s).hexdigest()


VERSION = 1

FILTER_MAX_PATH_DEPTH = 2

class Comment:
    columns = [column.name for column in db.schema['code_comments'].columns]

    required = 'text', 'author'

    _email_map = None

    def __init__(self, req, env, data):
        if isinstance(data, dict):
            self.__dict__ = data
        else:
            self.__dict__ = dict(zip(self.columns, data))
        self.env = env
        self.req = req
        if self._empty('version'):
            self.version = VERSION
        self.html = format_to_html(self.req, self.env, self.text)
        email = self.email_map().get(self.author, 'baba@baba.net')
        self.email_md5 = md5_hexdigest(email)
        attachment_info = self.attachment_info()
        self.is_comment_to_attachment = attachment_info['is']
        self.attachment_ticket = attachment_info['ticket']
        self.attachment_filename = attachment_info['filename']
        self.is_comment_to_changeset = self.revision and not self.path
        self.is_comment_to_file = self.revision and self.path

    def _empty(self, column_name):
        return not hasattr(self, column_name) or not getattr(self, column_name)

    def email_map(self):
        if self._email_map is None:
            self._email_map = {}
            for username, name, email in self.env.get_known_users():
                if email:
                    self._email_map[username] = email
        return self._email_map

    def validate(self):
        missing = [column_name for column_name in self.required if self._empty(column_name)]
        if missing:
            raise ValueError("Comment column(s) missing: %s" % ', '.join(missing))

    def href(self):
        if self.is_comment_to_file:
            href = self.req.href.browser(self.path, rev=self.revision, codecomment=self.id)
        elif self.is_comment_to_changeset:
            href = self.req.href.changeset(self.revision, codecomment=self.id)
        elif self.is_comment_to_attachment:
            href = self.req.href('/attachment/ticket/%d/%s' % (self.attachment_ticket, self.attachment_filename), codecomment=self.id)
        if self.line:
            href += '#L' + str(self.line)
        return href

    def link_text(self):
        if self.revision and not self.path:
            return '[%s]' % self.revision
        if self.path.startswith('attachment:'):
            return self.attachment_link_text()

        # except the two specials cases of changesets (revision-only)
        # and arrachments (path-only), we must always have them both
        assert self.path and self.revision
        
        link_text = self.path + '@' + str(self.revision)
        if self.line:
            link_text += '#L' + str(self.line)
        return link_text
    
    def attachment_link_text(self):
        return '#%s: %s' % (self.attachment_ticket, self.attachment_filename)

    def trac_link(self):
        if self.is_comment_to_attachment:
            return '[%s %s]' % (self.req.href())
        return 'source:' + self.link_text()
        
    def attachment_info(self):
        info = {'is': False, 'ticket': None, 'filename': None}
        info['is'] = self.path.startswith('attachment:')
        if not info['is']:
            return info
        match = re.match(r'attachment:/ticket/(\d+)/(.*)', self.path)
        if not match:
            return info
        info['ticket'] = int(match.group(1))
        info['filename'] = match.group(2)
        return info

    def path_link_tag(self):
        return Markup('<a href="%s">%s</a>' % (self.href(), self.link_text()))
        
    def formatted_date(self):
        return strftime('%d %b %Y, %H:%M', gmtime(self.time))
        
    def get_ticket_relations(self):
        relations = set()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        query = """SELECT ticket FROM ticket_custom WHERE name = 'code_comment_relation' AND 
                        (value LIKE '%(comment_id)d' OR
                         value LIKE '%(comment_id)d,%%' OR
                         value LIKE '%%,%(comment_id)d' OR value LIKE '%%,%(comment_id)d,%%')""" % {'comment_id': self.id}
        result = {}
        @self.env.with_transaction()
        def get_ticket_ids(db):
            cursor = db.cursor()
            cursor.execute(query)
            result['tickets'] = cursor.fetchall()
        return set([int(row[0]) for row in result['tickets']])
        
    def get_ticket_links(self):
        relations = self.get_ticket_relations()
        links = ['[[ticket:%s]]' % relation for relation in relations]
        return format_to_html(self.req, self.env, ', '.join(links))

    def get_tickets_for_dropdown(self):
        relations = self.get_ticket_relations()
        links = ['[[ticket:%s]]' % relation for relation in relations]
        res = {}
        for link in links:
            link_html = format_to_html(self.req, self.env, link)
            if link_html:
                # <a class="new ticket" href="/ticket/9" title="defect: just testing (new)">9</a>
                pattern = "<a.+href=\"(.+)\" title=\"(.+)\">(.+)</a>"
                for match in re.finditer(pattern, link_html, re.I):
                    res[int(match.group(3))] = {'title': match.group(2), 'link': match.group(1), 'ticket_id': int(match.group(3)), 'code_comments': [str(self.id)]}
        return res
        
    def delete(self):
        @self.env.with_transaction()
        def delete_comment(db):
            cursor = db.cursor()
            cursor.execute("DELETE FROM code_comments WHERE id=%s", [self.id])

class CommentJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Comment):
            for_json = dict([(name, getattr(o, name)) for name in o.__dict__ if isinstance(getattr(o, name), (basestring, int, list, dict))])
            for_json['formatted_date'] = o.formatted_date()
            for_json['permalink'] = o.href()
            return for_json
        else:
            return json.JSONEncoder.default(self, o)

class Comments:
    def __init__(self, req, env):
        self.req, self.env = req, env

    def comment_from_row(self, row):
        return Comment(self.req, self.env, row)

    def get_filter_values(self):
        comments = self.all()
        return {
            'paths': self.get_all_paths(comments),
            'authors': self.get_all_comment_authors(comments),
            'tickets': self.get_all_tickets(comments),
        }
        
    def get_all_paths(self, comments):
        get_directory = lambda path: '/'.join(os.path.split(path)[0].split('/')[:FILTER_MAX_PATH_DEPTH])
        return sorted(set([get_directory(comment.path) for comment in comments if get_directory(comment.path)]))
         
    def get_all_comment_authors(self, comments):
        return sorted(list(set([comment.author for comment in comments])))
        
    def get_all_tickets(self, comments):
        tickets = {}
        for comment in comments:
            comments_join = []
            ticket_links =  comment.get_tickets_for_dropdown()
            if ticket_links:
                for ticket_id, ticket in ticket_links.items():
                    if ticket_id not in tickets:
                        tickets[ticket_id] = ticket
                    else:
                        for code_comment in ticket['code_comments']:
                            if code_comment not in tickets[ticket_id]['code_comments']:
                                tickets[ticket_id]['code_comments'].append(code_comment)

        if tickets:
            for ticket_id, ticket in tickets.items():
                tickets[ticket_id]['code_comments_like'] = ",".join(tickets[ticket_id]['code_comments'])
        return tickets
        
        
    def select(self, *query):
        result = {}
        @self.env.with_transaction()
        def get_comments(db):
            cursor = db.cursor()
            cursor.execute(*query)
            result['comments'] = cursor.fetchall()
        return [self.comment_from_row(row) for row in result['comments']]

    def all(self):
        return self.search({}, order='DESC')

    def by_id(self, id):
        return self.select("SELECT * FROM code_comments WHERE id=%s", [id])[0]
        
    def assert_name(self, name):
        if not name in Comment.columns:
            raise ValueError("Column '%s' doesn't exist." % name)

    def search(self, args, order = 'ASC'):
        conditions = []
        values = []
        for name in args:
            if not name.endswith('__in') and not name.endswith('__prefix'):
                values.append(args[name])
            if name.endswith('__gt'):
                name = name.replace('__gt', '')
                conditions.append(name + ' > %s')
            elif name.endswith('__lt'):
                name = name.replace('__lt', '')
                conditions.append(name + ' < %s')
            elif name.endswith('__prefix'):
                values.append(args[name].replace('%', '\\%').replace('_', '\\_') + '%')
                name = name.replace('__prefix', '')
                conditions.append(name + ' LIKE %s')
            elif name.endswith('__in'):
                items = [item.strip() for item in args[name].split(',')]
                name = name.replace('__in', '')
                for item in items:
                    values.append(item)
                conditions.append(name + ' IN (' + ','.join(['%s']*len(items)) + ')')
            else:
                conditions.append(name + ' = %s')
            # don't let SQL injections in - make sure the name is an existing comment column
            self.assert_name(name)
        conditions_str = ' AND '.join(conditions)
        where = ''
        if conditions_str:
            where = 'WHERE '+conditions_str
        if order != 'ASC':
            order = 'DESC'
        return self.select('SELECT * FROM code_comments ' + where + ' ORDER BY time '+order, values)

    def create(self, args):
        comment = Comment(self.req, self.env, args)
        comment.validate()
        comment.time = int(time())
        values = [getattr(comment, column_name) for column_name in comment.columns if column_name != 'id']
        comment_id = [None]
        @self.env.with_transaction()
        def insert_comment(db):
            cursor = db.cursor()
            sql = "INSERT INTO code_comments values(NULL, %s)" % ', '.join(['%s'] * len(values))
            cursor.execute(sql, values)
            comment_id[0] = db.get_last_id(cursor, 'code_comments')
        return comment_id[0]

def format_to_html(req, env, text):
    context = Context.from_request(req)
    return trac.wiki.formatter.format_to_html(env, context, text)