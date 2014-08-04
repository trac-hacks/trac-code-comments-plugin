from trac.attachment import Attachment
from trac.config import BoolOption
from trac.core import Component, implements
from trac.notification import NotifyEmail
from trac.resource import ResourceNotFound
from trac.versioncontrol import RepositoryManager, NoSuchChangeset
from code_comments.api import ICodeCommentChangeListener
from code_comments.comments import Comments


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

    def _get_attachment_author(self, parent, parent_id, filename):
        """
        Returns the author of a given attachment.
        """
        try:
            attachment = Attachment(self.env, parent, parent_id, filename)
            return attachment.author
        except ResourceNotFound:
            self.env.log.debug("Invalid attachment, unable to determine "
                               "author.")

    def _get_changeset_author(self, revision, reponame=None):
        """
        Returns the author of a changeset for a given revision.
        """
        try:
            repos = RepositoryManager(self.env).get_repository(reponame)
            changeset = repos.get_changeset(revision)
            return changeset.author
        except NoSuchChangeset:
            self.env.log.debug("Invalid changeset, unable to determine author")

    def _get_original_author(self, comment):
        """
        Returns the author for the target of a given comment.
        """
        if comment.type == 'attachment':
            parent, parent_id, filename = comment.path.split("/")[1:]
            return self._get_attachment_author(parent, parent_id,
                                               filename)
        elif (comment.type == 'changeset' or comment.type == "browser"):
            # TODO: When support is added for multiple repositories, this
            # will need updated
            return self._get_changeset_author(comment.revision)

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

    def _get_commenters(self, comment):
        """
        Returns a list of all commenters for the same thing.
        """
        comments = Comments(None, self.env)
        args = {'type': comment.type,
                'revision': comment.revision,
                'path': comment.path}
        return comments.get_all_comment_authors(comments.search(args))

    def get_recipients(self, comment):
        """
        Determine who should receive the notification.

        Required by NotifyEmail.

        Current scheme is as follows:

         * For the first comment in a given location, the notification is sent
         'to' the original author of the thing being commented on, and 'copied'
         to the authors of any other comments on that thing
         * For any further comments in a given location, the notification is
         sent 'to' the author of the last comment in that location, and
         'copied' to both the original author of the thing and the authors of
         any other comments on that thing
        """
        torcpts = set()

        # Get the original author
        original_author = self._get_original_author(comment)

        # Get other commenters
        ccrcpts = set(self._get_commenters(comment))

        # Is this a reply, or a new comment?
        thread = self._get_comment_thread(comment)
        if len(thread) > 1:
            # The author of the comment before this one
            torcpts.add(thread[-2].author)
            # Copy to the original author
            ccrcpts.add(original_author)
        else:
            # This is the first comment in this thread
            torcpts.add(original_author)

        # Should we notify the comment author?
        if not self.notify_self:
            torcpts = torcpts.difference([comment.author])
            ccrcpts = ccrcpts.difference([comment.author])

        # Remove duplicates
        ccrcpts = ccrcpts.difference(torcpts)

        self.env.log.debug("Sending notification to: %s" % torcpts)
        self.env.log.debug("Copying notification to: %s" % ccrcpts)

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
        })

        projname = self.config.get("project", "name")
        subject = "Re: [%s] %s" % (projname, comment.link_text())

        NotifyEmail.notify(self, comment, subject)

    def send(self, torcpts, ccrcpts):
        """
        Override NotifyEmail.send() so we can provide from_name.
        """
        self.from_name = self.comment_author
        NotifyEmail.send(self, torcpts, ccrcpts)
