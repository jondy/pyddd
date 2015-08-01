#!/usr/bin/env python

import sys
import os
from distutils.core import setup, Extension

def get_description():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), 'README.rst'))
    f = open(filename, 'r')
    try:
        return f.read()
    finally:
        f.close()

VERSION = '0.2.1'

def main():
    setup_args = dict(
        name='pyddd',
        version=VERSION,
        description='Pyddd is a super-GDB debugger ' \
                    'used to debug python scripts line by line in GDB',
        long_description=get_description(),
        keywords=['debug', 'gdb', 'pdb'],
        py_modules=['libddd'],
        ext_modules=[Extension('python-ipa', ['ipa.c', 'ipa.h'],
            extra_compile_args=['-g',],
            libraries=['pthread',]),],
        author='Jondy Zhao',
        author_email='jondy.zhao@gmail.com',
        maintainer='Jondy Zhao',
        maintainer_email='jondy.zhao@gmail.com',
        url='https://github.com/jondy/pyddd',
        platforms=['Windows', 'Linux'],
        license='GPLv3',
        )
    setup(**setup_args)

if __name__ == '__main__':
    main()
