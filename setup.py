import re

import setuptools
from setuptools import find_packages


def find_version():
    return re.search(r"^__version__ = '(.*)'$",
                     open('gqt/version.py', 'r').read(),
                     re.MULTILINE).group(1)


setuptools.setup(
    name='gqt',
    version=find_version(),
    description='GraphQL client in the terminal.',
    long_description=open('README.rst', 'r').read(),
    author='Erik Moqvist',
    author_email='erik.moqvist@gmail.com',
    license='MIT',
    url='https://github.com/eerimoq/gqt',
    install_requires=[
        'requests',
        'xdg',
        'pyyaml',
        'readlike',
        'graphql-core',
        'tabulate'
    ],
    packages=find_packages(exclude=['tests']),
    test_suite="tests",
      entry_points = {
          'console_scripts': ['gqt=gqt.__init__:main']
      })
