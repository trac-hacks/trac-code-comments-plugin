# -*- coding: utf-8 -*-

from trac.core import Component, implements
from trac.ticket.api import ITicketChangeListener

import re

from code_comments.comment_macro import CodeCommentLinkMacro


class UpdateTicketCodeComments(Component):
    """Automatically stores relations to CodeComments whenever a ticket
    is saved or created
    Note: This does not catch edits on replies right away but on the next
    change of the ticket or when adding a new reply
    """

    implements(ITicketChangeListener)

    def ticket_created(self, ticket):
        self.update_relations(ticket)

    def ticket_changed(self, ticket, comment, author, old_values):
        self.update_relations(ticket)

    def ticket_deleted(self, ticket):
        self.update_relations(ticket)

    def update_relations(self, ticket):
        comment_ids = []
        # (time, author, field, oldvalue, newvalue, permanent)
        changes = ticket.get_changelog()
        description = ticket['description']

        comment_ids += re.findall(CodeCommentLinkMacro.re, description)
        if changes:
            for change in changes:
                if change[2] == 'comment':
                    comment_ids += re.findall(CodeCommentLinkMacro.re,
                                              change[4])

        comment_ids = set(comment_ids)
        comment_ids_csv = ','.join(comment_ids)

        with self.env.db_transaction as db:
            for _ in db("""
                    SELECT * FROM ticket_custom
                    WHERE ticket=%s AND name = 'code_comment_relation'
                    """, (ticket.id,)):
                db("""
                    UPDATE ticket_custom SET value=%s
                    WHERE ticket=%s AND name='code_comment_relation'
                    """, (comment_ids_csv, ticket.id))
                break
            else:
                db("""
                    INSERT INTO ticket_custom (ticket, name, value)
                    VALUES (%s, 'code_comment_relation', %s)
                    """, (ticket.id, comment_ids_csv))
