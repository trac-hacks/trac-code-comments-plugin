# -*- coding: utf-8 -*-

from trac.config import BoolOption
from trac.core import Component, implements
from trac.notification.api import NotificationEvent, NotificationSystem, INotificationSubscriber, INotificationFormatter, IEmailDecorator
from trac.notification.mail import RecipientMatcher, set_header
from trac.notification.model import Subscription
from trac.web.chrome import Chrome
from trac.util.datefmt import datetime_now, utc

from code_comments.api import ICodeCommentChangeListener
from code_comments.comments import Comments
from code_comments.subscription import Subscription as CcSubscription

CODE_COMMENT_REALM = 'code-comment'


class CodeCommentChangeEvent(NotificationEvent):
    """
    This class represents a notification event for a code-comment.
    """

    def __init__(self, category, comment):
        super(CodeCommentChangeEvent, self).__init__(
            CODE_COMMENT_REALM,
            category,
            comment,
            time=datetime_now(utc),
            author=comment.author,
        )


class CodeCommentChangeListener(Component):
    """
    Publishes notifications when comments have been created.
    """
    implements(ICodeCommentChangeListener)

    # ICodeCommentChangeListener methods

    def comment_created(self, comment):
        event = CodeCommentChangeEvent('created', comment)
        NotificationSystem(self.env).notify(event)


class _CodeCommentNotificationSubscriberMixin(object):
    """
    This mixin class defines useful methods for all classes implementing INotificationSubscriber.
    """

    def _get_default_subscriptions(self, recipient):
        sid, auth, addr = recipient
        return [
            (s[0], s[1], sid, auth, addr, s[2], s[3], s[4])
            for s in self.default_subscriptions()
        ]

    def _get_existing_subscriptions(self, sids):
        klass = self.__class__.__name__
        return [
            s.subscription_tuple()
            for s in Subscription.find_by_sids_and_class(self.env, sids, klass)
        ]


class CodeCommentNotificationSubscriberSelf(_CodeCommentNotificationSubscriberMixin, Component):
    """
    Allows to block notifications for the users own code-comments.
    """

    implements(INotificationSubscriber)

    notify_self = BoolOption('code_comments', 'notify_self', False,
                             doc="Send comment notifications to the author of "
                                 "the comment.")

    def matches(self, event):
        if event.realm != CODE_COMMENT_REALM:
            return []

        comment = event.target
        recipient = RecipientMatcher(self.env).match_recipient(comment.author)
        if not recipient:
            return []

        result = self._get_default_subscriptions(recipient)

        sid, auth, _ = recipient
        if sid:
            result += self._get_existing_subscriptions([(sid, auth)])

        return result

    def description(self):
        return "I make a code-comment"

    def requires_authentication(self):
        return True

    def default_subscriptions(self):
        if not self.notify_self:
            klass = self.__class__.__name__
            return [
                (klass, 'email', 'text/plain', 99, 'never'),
            ]
        return []


class CodeCommentNotificationSubscriberSubscribed(_CodeCommentNotificationSubscriberMixin, Component):
    """
    Allows to receive notifications for subscribed revisions/files/attachments.
    """

    implements(INotificationSubscriber)

    def _get_recipients(self, comment):
        recipients = set()
        for subscription in CcSubscription.for_comment(self.env, comment,
                                                       notify=True):
            recipients.add(subscription.user)
        return recipients

    def matches(self, event):
        if event.realm != CODE_COMMENT_REALM:
            return []

        comment = event.target
        candidates = self._get_recipients(comment)

        result = []
        matcher = RecipientMatcher(self.env)
        sids = set()
        for candidate in candidates:
            recipient = matcher.match_recipient(candidate)
            if not recipient:
                continue

            result += self._get_default_subscriptions(recipient)
            sid, auth, _ = recipient
            if sid:
                sids.add((sid, auth))

        result += self._get_existing_subscriptions(sids)

        return result

    def description(self):
        return "A code-comment is made on a revision/file/attachment I'm subscribed to"

    def requires_authentication(self):
        return True

    def default_subscriptions(self):
        klass = self.__class__.__name__
        return [
            (klass, 'email', 'text/plain', 100, 'always'),
        ]


class CodeCommentNotificationSubscriberReply(_CodeCommentNotificationSubscriberMixin, Component):
    """
    Allows to receive notifications when a comment is being replied to.
    """

    implements(INotificationSubscriber)

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

    def matches(self, event):
        if event.realm != CODE_COMMENT_REALM:
            return []

        comment = event.target
        thread = self._get_comment_thread(comment)
        is_reply = len(thread) > 1
        if not is_reply:
            return []

        previous_author = thread[-2].author
        recipient = RecipientMatcher(self.env).match_recipient(previous_author)
        if not recipient:
            return []

        result = self._get_default_subscriptions(recipient)

        sid, auth, _ = recipient
        if sid:
            result += self._get_existing_subscriptions([(sid, auth)])

        return result

    def description(self):
        return "A code-comment is made as a reply to (directly following) one of my own code-comments"

    def requires_authentication(self):
        return True

    def default_subscriptions(self):
        klass = self.__class__.__name__
        return [
            (klass, 'email', 'text/plain', 100, 'always'),
        ]


class CodeCommentNotificationFormatter(Component):
    """
    Provides body and email headers for code-comment notifications.
    """

    implements(INotificationFormatter, IEmailDecorator)

    template_name = "code_comment_notify_email.txt"

    # IEmailDecorator methods

    def decorate_message(self, event, message, charset):
        if event.realm != CODE_COMMENT_REALM:
            return

        comment = event.target

        reply_to = RecipientMatcher(self.env).match_from_author(comment.author)
        if reply_to:
            set_header(message, 'Reply-To', reply_to, charset)

            sender_address = NotificationSystem(self.env).smtp_from
            if sender_address:
                set_header(message, 'From', (reply_to[0], sender_address), charset)

        projname = self.config.get("project", "name")
        subject = "Re: [%s] %s" % (projname, comment.link_text())
        set_header(message, 'Subject', subject, charset)

    # INotificationFormatter methods

    def get_supported_styles(self, transport):
        yield 'text/plain', CODE_COMMENT_REALM

    def format(self, transport, style, event):
        if event.realm != CODE_COMMENT_REALM:
            return

        comment = event.target
        chrome = Chrome(self.env)

        template, data = chrome.prepare_template(
            req=None,
            filename=self.template_name,
            data=None,
            text=True,
        )

        data.update({
            "comment": comment,
            "comment_url": self.env.abs_href() + comment.href(),
            "project_url": self.env.project_url or self.env.abs_href(),
        })

        body = chrome.render_template_string(template, data, text=True)
        return body.encode('utf-8')
