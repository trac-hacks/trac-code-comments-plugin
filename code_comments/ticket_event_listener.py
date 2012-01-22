from trac.core import *
from trac.ticket.api import ITicketChangeListener

import re

class UpdateTicketCodeComments(Component):
    """Automatically stores relations to CodeComments whenever a ticket is saved or created
    Note: This does not catch edits on replies right away but on the next change of the ticket or when adding a new reply
    """

    implements(ITicketChangeListener)

    def ticket_created(self, ticket):
        self.update_relations(ticket)
        
    def ticket_changed(self, ticket, comment, author, old_values):
        self.update_relations(ticket)

    def ticket_deleted(self, ticket):
        self.update_relations(ticket)

    def update_relations(self, ticket):
        code_comments = {}
        # (time, author, field, oldvalue, newvalue, permanent)
        changes = ticket.get_changelog()
        description = ticket['description']
        ticket_id = ticket.id
        code_comments = self.findall( "\[\[CodeCommentLink\(([0-9]+)[,|\)]+", description, code_comments )
        if changes:
            for change in changes:
                if change[2] == 'comment':
                    code_comments = self.findall( "\[\[CodeCommentLink\(([0-9]+)[,|\)]+", change[4], code_comments )
        
        if code_comments:
            existing_comments_query = """SELECT * FROM ticket_custom WHERE ticket = %(ticket_id)s AND name = 'code_comment_relation'""".lstrip() % {'ticket_id': ticket_id}
            existing_comments = self.do_query( existing_comments_query )
            if existing_comments:
                insert_query = """UPDATE ticket_custom SET value = '%(code_comment)s' WHERE ticket = %(ticket_id)s AND name = 'code_comment_relation'""".lstrip() % {'ticket_id': ticket_id, 'code_comment': ",".join(code_comments)}
            else:
                insert_query = """INSERT INTO ticket_custom (ticket,name,value) VALUES (%(ticket_id)s, 'code_comment_relation', '%(code_comment)s')""".lstrip() % {'ticket_id': ticket_id, 'code_comment': ",".join(code_comments)}
            self.do_query(insert_query)
        else:
            del_query = """UPDATE ticket_custom SET value = '' WHERE ticket = %(ticket_id)s AND name = 'code_comment_relation'""".lstrip() % {'ticket_id': ticket_id}
            self.do_query(del_query)
            
    def do_query(self, query):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            db.commit()
            return result
        except:
            return False
    
    def findall(self, pattern, string, res):
        for match in re.finditer(pattern, string, re.I):
            res[match.group(1)] = match.group(1)
        return res
