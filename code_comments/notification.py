from trac import __version__
from trac.config import BoolOption, Option
from trac.core import Component, implements
from trac.notification import NotifyEmail, NotificationSystem
from trac.util.translation import deactivate, reactivate

from code_comments.api import ICodeCommentChangeListener
from code_comments.comments import Comments
from code_comments.subscription import Subscription


class CodeCommentChangeListener(Component):
    """
    Sends email notifications when comments have been created.
    """
    implements(ICodeCommentChangeListener)

    # ICodeCommentChangeListener methods

    def comment_created(self, comment):
        notifier = CodeCommentNotifyEmail(self.env)
        notifier.notify(comment)


class CodeCommentNotifyEmail(NotifyEmail):
    """
    Sends code comment notifications by email.
    """

    notify_self = BoolOption('code_comments', 'notify_self', False,
                             doc="Send comment notifications to the author of "
                                 "the comment.")
    smtp_always_cc = Option('code_comments', 'smtp_always_cc', 'default',
                            doc="Email address(es) to always send notifications"
                                " to, addresses can be seen by all recipients"
                                "(Cc:).")

    smtp_always_bcc = Option('code_comments', 'smtp_always_bcc', 'default',
                             doc="Email address(es) to always send "
                                 "notifications to addresses do not appear "
                                 "publicly (Bcc:).")

    template_name = "code_comment_notify_email.txt"
    from_email = "trac+comments@localhost"

    def _get_comment_thread(self, comment):
        """
        Returns all comments in the same location as a given comment, sorted
        in order of id.
        """
        comments = Comments(None, self.env)
        args = {'type': comment.type,
                'revision': comment.revision,
                'path': comment.path,
                'line': comment.line}
        return comments.search(args, order_by='id')

    def get_recipients(self, comment):
        """
        Determine who should receive the notification.

        Required by NotifyEmail.

        Current scheme is as follows:

         * For the first comment in a given location, the notification is sent
         to any subscribers to that resource
         * For any further comments in a given location, the notification is
         sent to the author of the last comment in that location, and any other
         subscribers for that resource
        """
        torcpts = set()
        ccrcpts = set()

        for subscription in Subscription.for_comment(self.env, comment,
                                                     notify=True):
            torcpts.add(subscription.user)

        # Is this a reply, or a new comment?
        thread = self._get_comment_thread(comment)
        if len(thread) > 1:
            # The author of the comment before this one
            torcpts.add(thread[-2].author)

        # Should we notify the comment author?
        if not self.notify_self:
            torcpts = torcpts.difference([comment.author])
            ccrcpts = ccrcpts.difference([comment.author])

        # Remove duplicates
        ccrcpts = ccrcpts.difference(torcpts)

        return (torcpts, ccrcpts)

    def _get_author_name(self, comment):
        """
        Get the real name of the user who made the comment. If it cannot be
        determined, return their username.
        """
        for username, name, email in self.env.get_known_users():
            if username == comment.author and name:
                return name

        return comment.author

    def notify(self, comment):
        self.comment_author = self._get_author_name(comment)

        self.data.update({
            "comment": comment,
            "comment_url": self.env.abs_href() + comment.href(),
            "project_url": self.env.project_url or self.env.abs_href(),
        })

        projname = self.config.get("project", "name")
        subject = "Re: [%s] %s" % (projname, comment.link_text())

        try:
            NotifyEmail.notify(self, comment, subject)
        except Exception, e:
            self.env.log.error("Failure sending notification on creation of "
                               "comment #%d: %s", comment.id, e)

    def send(self, torcpts, ccrcpts, mime_headers={}):
        from email.MIMEText import MIMEText
        from email.Utils import formatdate
        self.from_name = self.comment_author
        stream = self.template.generate(**self.data)
        # don't translate the e-mail stream
        t = deactivate()
        try:
            body = stream.render('text', encoding='utf-8')
        finally:
            reactivate(t)
        public_cc = self.config.getbool('notification', 'use_public_cc')
        headers = {}
        headers['X-Mailer'] = 'Trac %s, by Edgewall Software' % __version__
        headers['X-Trac-Version'] = __version__
        headers['X-Trac-Project'] = self.env.project_name
        headers['X-URL'] = self.env.project_url
        headers['Precedence'] = 'bulk'
        headers['Auto-Submitted'] = 'auto-generated'
        headers['Subject'] = self.subject
        headers['From'] = (self.from_name, self.from_email) if self.from_name \
                           else self.from_email
        headers['Reply-To'] = self.replyto_email

        def build_addresses(rcpts):
            """Format and remove invalid addresses"""
            return filter(lambda x: x, \
                          [self.get_smtp_address(addr) for addr in rcpts])

        def remove_dup(rcpts, all):
            """Remove duplicates"""
            tmp = []
            for rcpt in rcpts:
                if not rcpt in all:
                    tmp.append(rcpt)
                    all.append(rcpt)
            return (tmp, all)

        toaddrs = build_addresses(torcpts)
        ccaddrs = build_addresses(ccrcpts)
        accparam = self.config.get('code_comments', 'smtp_always_cc')
        if accparam == "default":
            accparam = self.config.get('notification', 'smtp_always_cc') 
        accaddrs = accparam and \
                   build_addresses(accparam.replace(',', ' ').split()) or []
        bccparam = self.config.get('code_comments', 'smtp_always_bcc')
        if bccparam == "default":
            bccparam = self.config.get('notification', 'smtp_always_bcc')
        bccaddrs = bccparam and \
                   build_addresses(bccparam.replace(',', ' ').split()) or []

        recipients = []
        (toaddrs, recipients) = remove_dup(toaddrs, recipients)
        (ccaddrs, recipients) = remove_dup(ccaddrs, recipients)
        (accaddrs, recipients) = remove_dup(accaddrs, recipients)
        (bccaddrs, recipients) = remove_dup(bccaddrs, recipients)

        # if there is not valid recipient, leave immediately
        if len(recipients) < 1:
            self.env.log.info("no recipient for a ticket notification")
            return

        pcc = accaddrs
        if public_cc:
            pcc += ccaddrs
            if toaddrs:
                headers['To'] = ', '.join(toaddrs)
        if pcc:
            headers['Cc'] = ', '.join(pcc)
        headers['Date'] = formatdate()
        msg = MIMEText(body, 'plain')
        # Message class computes the wrong type from MIMEText constructor,
        # which does not take a Charset object as initializer. Reset the
        # encoding type to force a new, valid evaluation
        del msg['Content-Transfer-Encoding']
        msg.set_charset(self._charset)
        self.add_headers(msg, headers)
        self.add_headers(msg, mime_headers)
        NotificationSystem(self.env).send_email(self.from_email, recipients,
                                                msg.as_string())
