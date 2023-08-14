#!/usr/bin/env python
from setuptools import *
setup(
	py_modules = ['version'],
	entry_points={'console_scripts': ['version=version:_main']},
	name='version',
	url='http://gfxmonk.net/dist/0install/version.xml',
	install_requires=[],
	version='0.14.1',
)
