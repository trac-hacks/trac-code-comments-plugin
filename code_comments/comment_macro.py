from genshi.core import Markup
from trac.wiki.macros import WikiMacroBase
from code_comments.comments import Comments, CommentJSONEncoder, format_to_html
from trac.wiki import Formatter
import StringIO

class CodeCommentsMacro(WikiMacroBase):
    """CodeComments macro.
        This macro is used to embed a comment in a ticket or wiki page
        The first parameter is the comment id, if a second parameter is set to true it will also show the comment text
        usage examples: 
        {{{
        [[CodeComments(1)]]
        [[CodeComments(1,true)]]
        }}}
    """
    
    revision = "$Rev$"
    url = "$URL$"
    
    def expand_macro(self, formatter, name, text, args):
        self.req = formatter.req
        self.env = formatter.env
        text_split = text.split(',');
        id = text_split[0];
        show_description = False
        description = ''
        try:
            if text_split[1] == 'true':
                show_description = True
        except IndexError:
            show_description = False
            
        comment = Comments(self.req, self.env).by_id(id)
        if not show_description:
            description += """[%(link)s %(path)s]""".lstrip() % {'link': comment.href(), 'path': comment.path_revision_line()}
        else:
            description += """[%(link)s %(path)s]

%(text)s""".lstrip() % {'link': comment.href(), 'path': comment.path_revision_line(), 'text': comment.text}
        out = StringIO.StringIO()
        Formatter(self.env, formatter.context).format(description, out)
        return Markup(out.getvalue())
