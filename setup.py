#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'aiohttp>=2.0.0',
    'inflection>=0.3.1',
    'multidict>=3.3.0',
    'jsonpointer>=1.10',
    'python-dateutil>=2.6.0',
    'trafaret>=0.11.0',
    'yarl>=0.13.0',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='aiohttp_json_api',
    version='0.31.0',
    description="JSON API driven by aiohttp",
    long_description=readme + '\n\n' + history,
    author="Vladimir Bolshakov",
    author_email='vovanbo@gmail.com',
    url='https://github.com/vovanbo/aiohttp_json_api',
    packages=[
        'aiohttp_json_api',
        'aiohttp_json_api.compat',
        'aiohttp_json_api.jsonpointer',
        'aiohttp_json_api.schema',
        'aiohttp_json_api.schema.abc',
    ],
    package_dir={'aiohttp_json_api':
                 'aiohttp_json_api'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='aiohttp_json_api',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
