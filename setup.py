from setuptools import find_packages, setup

setup(
    name='TracCodeComments', version='1.1.1',
    author='Nikolay Bachiyski, Thorsten Ott',
    author_email='nikolay@automattic.com, tott@automattic.com',
    description='Tool for leaving inline code comments',
    packages=find_packages(exclude=['*.tests*']),
    entry_points = {
        'trac.plugins': [
            'code_comments = code_comments',
        ],
    },
    package_data = {'code_comments': ['templates/*.html', 'templates/js/*.html', 'htdocs/*.*','htdocs/jquery-ui/*.*', 'htdocs/jquery-ui/images/*.*', 'htdocs/sort/*.*']},
)
