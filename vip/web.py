from trac.core import *
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_script, add_stylesheet, add_notice
from trac.web.main import IRequestHandler, IRequestFilter
from trac.util import Markup
from trac.versioncontrol.api import RepositoryManager
from vip.comments import Comments

class CodeComments(Component):
    implements(INavigationContributor, IRequestFilter, ITemplateProvider)

    href = 'code-comments'

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return self.href

    def get_navigation_items(self, req):
        yield 'mainnav', 'code-comments', Markup('<a href="%s">Code Comments</a>' % (
                 req.href('code-comments') ) )

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('vip', resource_filename(__name__, 'htdocs'))]

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        add_script(req, 'vip/code-comments.js')
        add_stylesheet(req, 'vip/vip.css')
        return handler

    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type

class ListComments(CodeComments):
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/' + self.href

    def process_request(self, req):
        data = {}
        data['reponame'], repos, path = RepositoryManager(self.env).get_repository_by_path('/')
        data['comments'] = Comments(req, self.env).all()
        return 'comments.html', data, None

class DeleteCommentForm(CodeComments):
    implements(IRequestHandler)

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/' + self.href + '/delete'

    def process_request(self, req):
        return self.form(req) if req.method == 'GET' else self.delete(req)

    def form(self, req):
        data = {}
        referrer = req.get_header('Referer')
        data['comment'] = Comments(req, self.env).by_id(req.args['id'])
        data['return_to'] = referrer
        return 'delete.html', data, None

    def delete(self, req):
        comment = Comments(req, self.env).by_id(req.args['id'])
        comment.delete()
        add_notice(req, 'Comment deleted.')
        req.redirect(req.args['return_to'] or req.href())

class BundleCommentsRedirect(CodeComments):
    implements(IRequestHandler)

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/' + self.href + '/bundle'

    def process_request(self, req):
        text = ''
        for id in req.args['ids'].split(','):
            comment = Comments(req, self.env).by_id(id)
            text += """
[%(link)s %(path)s]
%(text)

""".lstrip() % {'link': comment.trac_link(), 'path': comment.path_revision_line(), 'text': comment.text}
        req.redirect(req.href.newticket(description=text))