=======================================
`JSON API`_ implementation for aiohttp_
=======================================


.. image:: https://img.shields.io/pypi/v/aiohttp_json_api.svg
        :target: https://pypi.python.org/pypi/aiohttp_json_api

.. image:: https://img.shields.io/travis/vovanbo/aiohttp_json_api.svg
        :target: https://travis-ci.org/vovanbo/aiohttp_json_api

.. image:: https://readthedocs.org/projects/aiohttp-json-api/badge/?version=latest
        :target: https://aiohttp-json-api.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/vovanbo/aiohttp_json_api/shield.svg
     :target: https://pyup.io/repos/github/vovanbo/aiohttp_json_api/
     :alt: Updates


Introduction
------------

This project heavily inspired by py-jsonapi_ (author is `Benedikt Schmitt`_).
Some parts of this project is improved and refactored dev-schema_ branch of **py-jsonapi**.
At beginning of my project dev-schema_ branch was a great, but not working attempt to
implement JSON API via schema controllers.

Some of base entities of **py-jsonapi** was replaced with **aiohttp** server's objects,
some of it was devided into new separate entities (e.g. ``RequestContext``, ``Document`` etc).


* Free software: MIT license
* Documentation: https://aiohttp-json-api.readthedocs.io.


Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _JSON API: http://jsonapi.org
.. _aiohttp: http://aiohttp.readthedocs.io/en/stable/
.. _py-jsonapi: https://github.com/benediktschmitt/py-jsonapi
.. _dev-schema: https://github.com/benediktschmitt/py-jsonapi/tree/dev-schema
.. _`Benedikt Schmitt`: https://github.com/benediktschmitt
