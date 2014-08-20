from trac.config import BoolOption
from trac.core import Component, implements
from trac.notification import NotifyEmail

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

    def send(self, torcpts, ccrcpts):
        """
        Override NotifyEmail.send() so we can provide from_name.
        """
        self.from_name = self.comment_author
        NotifyEmail.send(self, torcpts, ccrcpts)
