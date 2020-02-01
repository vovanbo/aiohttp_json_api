#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'aiohttp>=3.6.0',
    'inflection>=0.3.1',
    'multidict>=4.5.0',
    'jsonpointer>=1.10',
    'python-dateutil>=2.8.0',
    'python-mimeparse>=1.6.0',
    'trafaret>=1.2.0',
    'yarl>=1.3.0',
]

setup(
    name='aiohttp_json_api',
    version='0.37.0',
    description='JSON API driven by aiohttp',
    long_description=readme + '\n\n' + history,
    author='Vladimir Bolshakov',
    author_email='vovanbo@gmail.com',
    url='https://github.com/vovanbo/aiohttp_json_api',
    packages=[
        'aiohttp_json_api',
        'aiohttp_json_api.fields',
    ],
    package_dir={'aiohttp_json_api': 'aiohttp_json_api'},
    include_package_data=True,
    install_requires=requirements,
    license='MIT license',
    zip_safe=False,
    keywords='aiohttp_json_api',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
    ],
    test_suite='tests',
)
