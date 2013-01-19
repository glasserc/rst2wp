#!/usr/bin/env python

'''Install script. Adjust it to the reality of the package.
'''

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='rst2wp',
    version="0.1.0",
    description='REST to Wordpress blogging tool',
    author='glasserc',
    author_email='',
    packages=['rst2wp', 'rst2wp.lib'],
    license='',
    url='https://github.com/glasserc/rst2wp',
    long_description=open('README.rst').read(),
    install_requires=[
        "pyxdg",
        "docutils",
        "python-magic",
        "PIL"],
    entry_points={
        "console_scripts": [
            "rst2wp = rst2wp.rst2wp:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "Environment :: Console",
    ],
)
