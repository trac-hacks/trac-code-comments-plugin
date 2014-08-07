from trac.core import Component, ExtensionPoint, Interface


class ICodeCommentChangeListener(Interface):
    """An interface for receiving comment change events."""

    def comment_created(comment):
        """New comment created."""


class CodeCommentSystem(Component):
    change_listeners = ExtensionPoint(ICodeCommentChangeListener)

    def comment_created(self, comment):
        """
        Emits comment_created event to all listeners.
        """
        for listener in self.change_listeners:
            listener.comment_created(comment)
