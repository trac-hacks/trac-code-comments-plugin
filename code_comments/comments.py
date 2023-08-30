# -*- coding: utf-8 -*-

import os.path
from time import time

from code_comments.api import CodeCommentSystem
from code_comments.comment import Comment


class Comments(object):

    FILTER_MAX_PATH_DEPTH = 2

    def __init__(self, req, env):
        self.req, self.env = req, env
        self.valid_sorting_methods = ('id', 'author', 'time', 'reponame', 'path', 'text')

    def comment_from_row(self, row):
        return Comment(self.req, self.env, row)

    def get_filter_values(self):
        comments = self.all()
        return {
            'paths': self.get_all_paths(comments),
            'authors': self.get_all_comment_authors(comments),
        }

    def get_all_paths(self, comments):
        def get_directory(path):
            parts = os.path.split(path)[0].split('/')
            return '/'.join(parts[:self.FILTER_MAX_PATH_DEPTH])
        paths = [
            get_directory(comment.path)
            for comment in comments if get_directory(comment.path)
        ]
        return sorted(set(paths))

    def get_all_comment_authors(self, comments):
        return sorted(list(set([comment.author for comment in comments])))

    def select(self, *query):
        return [self.comment_from_row(row)
                for row in self.env.db_query(*query)]

    def count(self, args={}):
        conditions_str, values = \
            self.get_condition_str_and_corresponding_values(args)
        where = ''
        if conditions_str:
            where = 'WHERE ' + conditions_str
        query = 'SELECT COUNT(*) FROM code_comments ' + where
        result = {}

        for count, in self.env.db_query(query, values):
            result['count'] = count

        return result['count']

    def all(self):
        return self.search({}, order='DESC')

    def by_id(self, id):
        return self.select("SELECT * FROM code_comments WHERE id=%s", [id])[0]

    def assert_name(self, name):
        if name not in Comment.columns:
            raise ValueError("Column '%s' doesn't exist." % name)

    def search(self, args, order='ASC', per_page=None, page=1,
               order_by='time'):
        if order_by not in self.valid_sorting_methods:
            order_by = 'time'
        conditions_str, values = \
            self.get_condition_str_and_corresponding_values(args)
        where = ''
        limit = ''
        if conditions_str:
            where = 'WHERE ' + conditions_str
        if order != 'ASC':
            order = 'DESC'
        if per_page:
            limit = ' LIMIT %d OFFSET %d' % (per_page, (page - 1) * per_page)
        return self.select('SELECT * FROM code_comments ' + where +
                           ' ORDER BY ' + order_by + ' ' + order + limit,
                           values)

    def get_condition_str_and_corresponding_values(self, args):
        conditions = []
        values = []
        for name in args:
            if not name.endswith('__in') and not name.endswith('__prefix'):
                values.append(args[name])
            if name.endswith('__gt'):
                name = name.replace('__gt', '')
                conditions.append(name + ' > %s')
            elif name.endswith('__lt'):
                name = name.replace('__lt', '')
                conditions.append(name + ' < %s')
            elif name.endswith('__prefix'):
                values.append(
                    args[name].replace('%', '\\%').replace('_', '\\_') + '%')
                name = name.replace('__prefix', '')
                conditions.append(name + ' LIKE %s')
            elif name.endswith('__in'):
                items = [item.strip() for item in args[name].split(',')]
                name = name.replace('__in', '')
                for item in items:
                    values.append(item)
                conditions.append(
                    name + ' IN (' + ','.join(['%s'] * len(items)) + ')')
            else:
                conditions.append(name + ' = %s')
            # Prevent SQL injections: make sure name is an existing column
            self.assert_name(name)
        conditions_str = ' AND '.join(conditions)
        return conditions_str, values

    def create(self, args):
        comment = Comment(self.req, self.env, args)
        comment.validate()
        comment.time = int(time())
        column_names_to_insert = [n for n in comment.columns if n != 'id']
        values = [getattr(comment, n) for n in column_names_to_insert]
        comment_id = [None]

        with self.env.db_transaction as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO code_comments (%s) VALUES(%s)
                """ % (', '.join(column_names_to_insert),
                       ', '.join(['%s'] * len(values))), values)
            comment_id[0] = db.get_last_id(cursor, 'code_comments')

        CodeCommentSystem(self.env).comment_created(
            Comments(self.req, self.env).by_id(comment_id[0]))

        return comment_id[0]
