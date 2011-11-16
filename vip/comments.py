from trac.core import *
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_script, add_stylesheet
from trac.web.main import IRequestHandler, IRequestFilter
from trac.util import escape, Markup
from trac.versioncontrol.api import RepositoryManager

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

    def process_request(self, req):
        data = {}

        rm = RepositoryManager(self.env)
        data['reponame'], repos, path = rm.get_repository_by_path('/')

        @self.env.with_transaction()
        def get_comments(db):
            cursor = db.cursor()
            cursor.execute("SELECT * FROM vip_comments")
            data['comments'] = cursor.fetchall()
        return 'comments.html', data, None

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('vip', resource_filename(__name__, 'htdocs'))]

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        add_script(req, 'vip/x.js')
        return handler

    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type


# create ticket
# http://trac-hacks.org/browser/xmlrpcplugin/trunk/tracrpc/ticket.py#L138

# req.authname