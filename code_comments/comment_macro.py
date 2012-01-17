from genshi.core import Markup
from trac.wiki.macros import WikiMacroBase

class CodeCommentsMacro(WikiMacroBase):
    """Simple HelloWorld macro.

    Note that the name of the class is meaningful:
     - it must end with "Macro"
     - what comes before "Macro" ends up being the macro name

    The documentation of the class (i.e. what you're reading)
    will become the documentation of the macro, as shown by
    the !MacroList macro (usually used in the WikiMacros page).
    """
    
    print 'i am here'
    
    revision = "$Rev$"
    url = "$URL$"

    def expand_macro(self, formatter, name, text, args):
        """Return some output that will be displayed in the Wiki content.

        `name` is the actual name of the macro (no surprise, here it'll be
        `'HelloWorld'`),
        `text` is the text enclosed in parenthesis at the call of the macro.
          Note that if there are ''no'' parenthesis (like in, e.g.
          [[HelloWorld]]), then `text` is `None`.
        `args` are the arguments passed when HelloWorld is called using a
        `#!HelloWorld` code block.
        """
        print 'i am here, too'
        return 'Hello World, text = %s, args = %s' % \
            (Markup.escape(text), Markup.escape(repr(args)))
