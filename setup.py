from setuptools import find_packages, setup

setup(
    name='TracCodeComments', version='0.1.6',
    packages=find_packages(exclude=['*.tests*']),
    entry_points = {
        'trac.plugins': [
            'code_comments = code_comments',
        ],
    },
    package_data = {'code_comments': ['templates/*.html', 'templates/js/*.html', 'htdocs/*.*','htdocs/jquery-ui/*.*', 'htdocs/jquery-ui/images/*.*']},
)