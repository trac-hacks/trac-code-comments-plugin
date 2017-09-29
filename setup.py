from setuptools import find_packages, setup

setup(
    name='TracCodeComments', version='1.2.0',
    author='Nikolay Bachiyski, Thorsten Ott',
    author_email='nikolay@automattic.com, tott@automattic.com',
    description='Tool for leaving inline code comments',
    packages=find_packages(exclude=['*.tests*']),
    entry_points={
        'trac.plugins': [
            'code_comments.comment = code_comments.comment',
            'code_comments.comment_macro = code_comments.comment_macro',
            'code_comments.comments = code_comments.comments',
            'code_comments.db = code_comments.db',
            'code_comments.notification = code_comments.notification',
            'code_comments.subscription = code_comments.subscription',
            'code_comments.ticket_event_listener = code_comments.ticket_event_listener',
            'code_comments.web = code_comments.web',
        ],
    },
    package_data={
        'code_comments': [
            'templates/*.html',
            'templates/*.txt',
            'templates/js/*.html',
            'htdocs/*.*',
            'htdocs/jquery-ui/*.*',
            'htdocs/jquery-ui/images/*.*',
            'htdocs/sort/*.*',
        ],
    },
)
