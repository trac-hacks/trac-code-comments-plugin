from trac.core import Component, ExtensionPoint, Interface


class ICodeCommentChangeListener(Interface):
    """An interface for receiving comment change events."""

    def comment_created(comment):
        """New comment created."""


class CodeCommentSystem(Component):
    change_listeners = ExtensionPoint(ICodeCommentChangeListener)
