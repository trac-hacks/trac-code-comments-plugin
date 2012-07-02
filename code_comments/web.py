import re
import copy
from trac.core import *
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_script, add_script_data, add_stylesheet, add_notice, add_link
from trac.web.main import IRequestHandler, IRequestFilter
from trac.util import Markup
from trac.util.text import to_unicode
from trac.util.presentation import Paginator
from trac.versioncontrol.api import RepositoryManager
from code_comments.comments import Comments
from code_comments.comment import CommentJSONEncoder, format_to_html

try:
    import json
except ImportError:
    import simplejson as json

class CodeComments(Component):
    implements(ITemplateProvider, IRequestFilter)

    href = 'code-comments'

    # ITemplateProvider methods
    def get_templates_dirs(self):
        return [self.get_template_dir()]

    def get_template_dir(self):
        from pkg_resources import resource_filename
        return resource_filename(__name__, 'templates')

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('code-comments', resource_filename(__name__, 'htdocs'))]

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        add_stylesheet(req, 'code-comments/code-comments.css')
        return template, data, content_type

class MainNavigation(CodeComments):
    implements(INavigationContributor)

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return self.href

    def get_navigation_items(self, req):
        if 'TRAC_ADMIN' in req.perm:
            yield 'mainnav', 'code-comments', Markup('<a href="%s">Code Comments</a>' % (
                     req.href(self.href) ) )

class JSDataForRequests(CodeComments):
    implements(IRequestFilter)

    js_templates = ['top-comments-block', 'comment', 'add-comment-dialog', 'line-comment', 'comments-for-a-line',]

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if data is None:
            return

        js_data = {
            'comments_rest_url': req.href(CommentsREST.href),
            'formatting_help_url': req.href.wiki('WikiFormatting'),
            'delete_url': req.href(DeleteCommentForm.href),
            'preview_url': req.href(WikiPreview.href),
            'templates': self.templates_js_data(),
            'active_comment_id': req.args.get('codecomment'),
            'username': req.authname,
            'is_admin': 'TRAC_ADMIN' in req.perm,
        }

        original_return_value = template, data, content_type
        if req.path_info.startswith('/changeset/'):
            js_data.update(self.changeset_js_data(req, data))
        elif req.path_info.startswith('/browser'):
            js_data.update(self.browser_js_data(req, data))
        elif re.match(r'/attachment/ticket/\d+/.*', req.path_info):
            js_data.update(self.attachment_js_data(req, data))
        else:
            return original_return_value

        add_script(req, 'code-comments/json2.js')
        add_script(req, 'code-comments/underscore-min.js')
        add_script(req, 'code-comments/backbone-min.js')
        # jQuery UI includes: UI Core, Interactions, Button & Dialog Widgets, Core Effects, custom theme
        add_script(req, 'code-comments/jquery-ui/jquery-ui.js')
        add_stylesheet(req, 'code-comments/jquery-ui/trac-theme.css')
        add_script(req, 'code-comments/jquery.ba-throttle-debounce.min.js')
        add_script(req, 'code-comments/code-comments.js')
        add_script_data(req, {'CodeComments': js_data})
        return original_return_value

    def templates_js_data(self):
        data = {}
        for name in self.js_templates:
            # we want to use the name as JS identifier and we can't have dashes there
            data[name.replace('-', '_')] = self.template_js_data(name)
        return data

    def changeset_js_data(self, req, data):
        return {'page': 'changeset', 'revision': data['new_rev'], 'path': '', 'selectorToInsertBefore': 'div.diff:first'}

    def browser_js_data(self, req, data):
        return {'page': 'browser', 'revision': data['rev'], 'path': data['path'], 'selectorToInsertBefore': 'table#info'}

    def attachment_js_data(self, req, data):
        path = req.path_info.replace('/attachment/', 'attachment:/')
        return {'page': 'attachment', 'revision': 0, 'path': path, 'selectorToInsertBefore': 'table#info'}

    def template_js_data(self, name):
        file_name = name + '.html'
        return to_unicode(open(self.get_template_dir() + '/js/' + file_name).read())



class ListComments(CodeComments):
    implements(IRequestHandler)

    COMMENTS_PER_PAGE = 50

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/' + self.href

    def process_request(self, req):
        req.perm.require('TRAC_ADMIN')

        self.data = {}
        self.args = {}
        self.req = req

        self.per_page = int(req.args.get('per-page', self.COMMENTS_PER_PAGE))
        self.page = int(req.args.get('page', 1))
        self.order_by = req.args.get('orderby', 'id')
        self.order = req.args.get('order', 'DESC')

        self.add_path_and_author_filters()

        self.comments = Comments(req, self.env);
        self.data['comments'] = self.comments.search(self.args, self.order, self.per_page, self.page, self.order_by)
        self.data['reponame'], repos, path = RepositoryManager(self.env).get_repository_by_path('/')
        self.data['can_delete'] = 'TRAC_ADMIN' in req.perm
        self.data['paginator'] = self.get_paginator()
        self.data['current_sorting_method'] = self.order_by
        self.data['current_order'] = self.order
        self.data['sortable_headers'] = []

        self.data.update(self.comments.get_filter_values())
        self.prepare_sortable_headers()

        return 'comments.html', self.data, None

    def post_process_request(self, req, template, data, content_type):
        add_stylesheet(req, 'code-comments/sort/sort.css')
        add_script(req, 'code-comments/code-comments-list.js')
        return template, data, content_type

    def add_path_and_author_filters(self):
        self.data['current_path_selection'] = '';
        self.data['current_author_selection'] = '';

        if self.req.args.get('filter-by-path'):
            self.args['path__prefix'] = self.req.args['filter-by-path'];
            self.data['current_path_selection'] = self.req.args['filter-by-path']
        if self.req.args.get('filter-by-author'):
            self.args['author'] = self.req.args['filter-by-author']
            self.data['current_author_selection'] = self.req.args['filter-by-author']

    def get_paginator(self):
        def href_with_page(page):
            args = copy.copy(self.req.args)
            args['page'] = page
            return self.req.href(self.href, args)
        paginator = Paginator(self.data['comments'], self.page-1, self.per_page, Comments(self.req, self.env).count(self.args))
        if paginator.has_next_page:
            add_link(self.req, 'next', href_with_page(self.page + 1), 'Next Page')
        if paginator.has_previous_page:
            add_link(self.req, 'prev', href_with_page(self.page - 1), 'Previous Page')
        shown_pages = paginator.get_shown_pages(page_index_count = 11)
        links = [{'href': href_with_page(page), 'class': None, 'string': str(page), 'title': 'Page %d' % page}
            for page in shown_pages]
        paginator.shown_pages = links
        paginator.current_page = {'href': None, 'class': 'current', 'string': str(paginator.page + 1), 'title': None}
        return paginator

    def prepare_sortable_headers(self):
        displayed_sorting_methods = ('id', 'author', 'time', 'path', 'text')
        displayed_sorting_method_names = ('ID', 'Author', 'Date', 'Path', 'Text')
        query_args = self.req.args
        if ( query_args.has_key('page') ):
            del query_args['page']
        for sorting_method, sorting_method_name in zip(displayed_sorting_methods, displayed_sorting_method_names):
            query_args['orderby'] = sorting_method
            html_class = 'header'
            if self.order_by == sorting_method:
                if 'ASC' == self.order:
                    query_args['order'] = 'DESC'
                    html_class += ' headerSortUp'
                else:
                    query_args['order'] = 'ASC'
                    html_class += ' headerSortDown'
            link = self.req.href(self.href, query_args)
            self.data['sortable_headers'].append({ 'name': sorting_method_name, 'link': link, 'html_class': html_class })

class DeleteCommentForm(CodeComments):
    implements(IRequestHandler)

    href = CodeComments.href + '/delete'

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/' + self.href

    def process_request(self, req):
        req.perm.require('TRAC_ADMIN')
        if 'GET' == req.method:
            return self.form(req)
        else:
            return self.delete(req)

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

    href = CodeComments.href + '/create-ticket'

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/' + self.href

    def process_request(self, req):
        text = ''
        for id in req.args['ids'].split(','):
            comment = Comments(req, self.env).by_id(id)
            text += """
[[CodeCommentLink(%(id)s)]]
%(comment_text)s

""".lstrip() % {'id': id, 'comment_text': comment.text}
        req.redirect(req.href.newticket(description=text))

class CommentsREST(CodeComments):
    implements(IRequestHandler)

    href = CodeComments.href + '/comments'

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/' + self.href)

    def return_json(self, req, data, code=200):
        req.send(json.dumps(data, cls=CommentJSONEncoder), 'application/json')

    def process_request(self, req):
        #TODO: catch errors
        if '/' + self.href == req.path_info:
            if 'GET' == req.method:
                self.return_json(req, Comments(req, self.env).search(req.args))
            if 'POST' == req.method:
                comments = Comments(req, self.env)
                id = comments.create(json.loads(req.read()))
                self.return_json(req, comments.by_id(id))

class WikiPreview(CodeComments):
    implements(IRequestHandler)

    href = CodeComments.href + '/preview'

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/' + self.href)

    def process_request(self, req):
        req.send(format_to_html(req, self.env, req.args.get('text', '')).encode('utf-8'))
