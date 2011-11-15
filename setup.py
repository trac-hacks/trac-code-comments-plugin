from setuptools import find_packages, setup

setup(
    name='TracVIP', version='0.1',
    packages=find_packages(exclude=['*.tests*']),
    entry_points = {
        'trac.plugins': [
            'vip = vip',
        ],
    },
)