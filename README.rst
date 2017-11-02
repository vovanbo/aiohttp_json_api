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
Some parts of this project is improved and refactored dev-schema_ branch
of **py-jsonapi**. At beginning of aiohttp-json-api_ this branch
was a great, but not finished implementation of JSON API with
*schema controllers*. Also, py-jsonapi_ is not asynchronous and use inside
self-implemented Request/Response classes.

Some of base entities of **py-jsonapi** was replaced with **aiohttp**
server's objects, some of it was divided into new separate entities
(e.g. `RequestContext` or `Registry`).

* Free software: MIT license
* Documentation: https://aiohttp-json-api.readthedocs.io


Requirements
------------

* **Python 3.5** or newer
* aiohttp_
* inflection_
* multidict_
* jsonpointer_
* dateutil_
* trafaret_


Todo
----

* Tutorials
* Improve documentation
* Tests
* Features description
* Customizable payload keys inflection (default is `dasherize` <-> `underscore`)
* Support for JSON API extensions (bulk creation etc.)
* Polymorphic relationships


Credits
-------

This package was created with Cookiecutter_ and the
`cookiecutter-pypackage`_ project template.


.. _aiohttp-json-api: https://github.com/vovanbo/aiohttp_json_api
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _cookiecutter-pypackage: https://github.com/audreyr/cookiecutter-pypackage
.. _JSON API: http://jsonapi.org
.. _aiohttp: http://aiohttp.readthedocs.io/en/stable/
.. _py-jsonapi: https://github.com/benediktschmitt/py-jsonapi
.. _dev-schema: https://github.com/benediktschmitt/py-jsonapi/tree/dev-schema
.. _`Benedikt Schmitt`: https://github.com/benediktschmitt
.. _inflection: https://inflection.readthedocs.io/en/latest/
.. _jsonpointer: https://python-json-pointer.readthedocs.io/en/latest/index.html
.. _dateutil: https://dateutil.readthedocs.io/en/stable/
.. _trafaret: http://trafaret.readthedocs.io/en/latest/
.. _multidict: http://multidict.readthedocs.io/en/stable/
