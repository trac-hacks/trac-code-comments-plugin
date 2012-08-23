import re
import locale

import trac.wiki.formatter
from trac.mimeview.api import Context
from time import strftime, localtime
from code_comments import db
from trac.util import Markup

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
        if Comment._email_map is None:
            Comment._email_map = {}
            for username, name, email in self.env.get_known_users():
                if email:
                    Comment._email_map[username] = email
        return Comment._email_map

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
        encoding = locale.getlocale()[1] if locale.getlocale()[1] else 'utf-8'
        return strftime('%d %b %Y, %H:%M', localtime(self.time)).decode(encoding)

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

def format_to_html(req, env, text):
    context = Context.from_request(req)
    return trac.wiki.formatter.format_to_html(env, context, text)
