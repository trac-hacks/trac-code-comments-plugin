from setuptools import find_packages, setup

setup(
    name='TracCodeComments', version='0.1.1',
    packages=find_packages(exclude=['*.tests*']),
    entry_points = {
        'trac.plugins': [
            'code_comments = code_comments',
        ],
    },
)