# -*- coding: utf-8 -*-

from code_comments.comments import Comments
from genshi.builder import tag
from trac.wiki.macros import WikiMacroBase


class CodeCommentLinkMacro(WikiMacroBase):
    """CodeCommentLink macro.
        This macro is used to embed a comment link in a ticket or wiki page:
        [[CodeCommentLink(5)]]
        where the number in the parentheses is the comment ID.
    """

    revision = "$Rev$"
    url = "$URL$"
    re = r'\[\[CodeCommentLink\((\d+)\)\]\]'

    def expand_macro(self, formatter, name, text, args):
        try:
            comment = Comments(formatter.req, formatter.env).by_id(text)
            return tag.a(comment.link_text(), href=comment.href())
        except:
            return ''
