#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import codecs
from setuptools import setup, find_packages


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


version = ''
with open('src/pytest_pyright/__init__.py') as f:
    match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE)
    if not match:
        raise RuntimeError('version is not set')

    version = match.group(1)

if not version:
    raise RuntimeError('version is not set')


setup(
    name='pytest-pyright',
    version=version,
    author='Robert Craigie',
    author_email='robertcraigie30@gmail.com',
    maintainer='Robert Craigie',
    maintainer_email='robertcraigie30@gmail.com',
    license='MIT',
    url='https://github.com/RobertCraigie/pytest-pyright',
    description='Pytest plugin for type checking code with Pyright',
    long_description=read('README.rst'),
    packages=find_packages(where='src', include=['pytest_pyright', 'pytest_pyright.*']),
    package_dir={'': 'src'},
    python_requires='>=3.7',
    install_requires=read('requirements.txt').splitlines(),
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'pyright = pytest_pyright.plugin',
        ],
    },
)
