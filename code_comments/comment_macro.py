from code_comments.comments import Comments, CommentJSONEncoder, format_to_html
from genshi.core import Markup
from genshi.builder import tag
from trac.wiki.macros import WikiMacroBase
from trac.wiki import Formatter
import StringIO

class CodeCommentLinkMacro(WikiMacroBase):
    """CodeCommentLink macro.
        This macro is used to embed a comment link in a ticket or wiki page:
        {{{
        [[CodeCommentLink(5)]]
        where the number in the parenthesis is the comment ID.
        }}}
    """
    
    revision = "$Rev$"
    url = "$URL$"
    
    def expand_macro(self, formatter, name, text, args):
        self.req = formatter.req
        self.env = formatter.env
        try:
            comment = Comments(self.req, self.env).by_id(text)
            return tag.a(comment.path_revision_line(), href=comment.href())
        except:
            return ''