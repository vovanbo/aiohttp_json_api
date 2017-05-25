#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_aiohttp_json_api
----------------------------------

Tests for `aiohttp_json_api` module.
"""

import pytest


from aiohttp_json_api import aiohttp_json_api


@pytest.fixture
def response():
    """Sample pytest fixture.
    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument.
    """
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string
