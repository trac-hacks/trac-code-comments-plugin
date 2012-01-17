from genshi.core import Markup
from trac.wiki.macros import WikiMacroBase
from code_comments.comments import Comments, CommentJSONEncoder, format_to_html
from trac.wiki import Formatter
import StringIO

class CodeCommentsMacro(WikiMacroBase):
    """CodeComments macro.
        This macro is used to embed a comment in a ticket or wiki page
        usage examples: 
        {{{
        [[CodeComments(1)]]
        {{{#!CodeComments description="alternative comment text"
        1
        }}}
        }}}
    """
    
    revision = "$Rev$"
    url = "$URL$"
    
    def expand_macro(self, formatter, name, text, args):
        self.req = formatter.req
        self.env = formatter.env
        description = ''
        for id in text.split(','):
            comment = Comments(self.req, self.env).by_id(id)
            if args and args['description']:
                comment_text = args['description']
            else:
                comment_text = comment.text
            description += """
[%(link)s %(path)s]

%(text)s
            """.lstrip() % {'link': comment.href(), 'path': comment.path_revision_line(), 'text': comment_text}
        out = StringIO.StringIO()
        Formatter(self.env, formatter.context).format(description, out)
        return Markup(out.getvalue())
