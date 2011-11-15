from trac.core import *
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_script, add_stylesheet
from trac.web.main import IRequestHandler, IRequestFilter
from trac.util import escape, Markup

class VIPComments(Component):
    implements(INavigationContributor, IRequestHandler, IRequestFilter, ITemplateProvider)
    
    href = 'code-comments'

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return self.href

    def get_navigation_items(self, req):
        yield 'mainnav', 'code-comments', Markup('<a href="%s">Code Comments</a>' % (
                 req.href('code-comments') ) )

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/' + self.href)

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
        
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('vip', resource_filename(__name__, 'htdocs'))]


    def process_request(self, req):
        return 'comments.html', {}, None

    def pre_process_request(self, req, handler):
        add_script(req, 'vip/x.js')
        return handler

    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type


# create ticket
# http://trac-hacks.org/browser/xmlrpcplugin/trunk/tracrpc/ticket.py#L138

# req.authname