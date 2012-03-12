#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='settings',
    version='0.1',
    description='Declarative Schema for parsing INI files',
    author='David Vincelli',
    author_email='david@freshbooks.com',
    url='https://github.com/ocim/settings',
    py_modules = ['settings'],
    test_suite = 'tests'
)
