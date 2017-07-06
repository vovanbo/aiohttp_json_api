=======
History
=======

0.9.2 (2017-07-06)
------------------

* Fix bugs related to Python 3.5
* Generation of documentation on RTD is fixed


0.9.1 (2017-07-06)
------------------

* Python 3.5 compatibility changes


0.9.0 (2017-07-06)
------------------

* Handle aiohttp-json-api exceptions and errors in middleware. If exceptions is not related to JSON API errors, then exception is reraised
* Huge refactoring of RequestContext
* No more use of boltons cachedproperties, instead use parsing static methods related to each request context' entity
* Update docs for RequestContext methods
* Add typings to RequestContext


0.8.2 (2017-07-05)
------------------

* Properly handle error with wrong relation name (raise HTTP 400)


0.8.1 (2017-07-05)
------------------

* Fix bdist_wheel python tag to support Python 3.5


0.8.0 (2017-07-05)
------------------

* Python 3.5 support (avoid usage of Python 3.6 format strings)
* Registry is plain object now
* Custom Registry support (`registry_class` parameter in ``aiohttp_json_api.setup_jsonapi`` method)
* Log debugging information at start about registered resources, methods and routes
* Use OrderedDict inside SchemaMeta


0.7.2 (2017-07-04)
------------------

* Fix bug with JSONPointer when part passed via __truediv__ is integer
* Validate relationship object before adding relationship in ToMany field


0.7.1 (2017-07-04)
------------------

* Fix bugs with validation of resource identifier in relationships fields
* Add typings for base fields


0.7.0 (2017-07-03)
------------------

* Setup of JSON API must be imported from package directly
* Fix bugs with decode fields and allow None values


0.6.2 (2017-06-29)
------------------

* Update HISTORY


0.6.1 (2017-06-29)
------------------

* Fix bug with Enum choices of String field


0.6.0 (2017-06-29)
------------------

* Return resource in update method of Schema class. This will be helpful in inherit classes of Schemas.


0.5.5 (2017-06-15)
------------------

* Setup auto-deploy to PyPI in Travis CI

0.5.4 (2017-06-15)
------------------

* Initial release on PyPI

0.5.3 (2017-06-14)
------------------

* Improve documentation

0.5.0 (2017-06-14)
------------------

* Don't use attrs_ package anymore
* Refactor requirements (move it into `setup.py`)

0.4.0 (2017-06-13)
------------------

* Schema imports refactoring (e.g. don't use ``aiohttp_json_api.schema.schema.Schema`` anymore)

0.3.0 (2017-06-13)
------------------

* Upgrade requirements

0.2.0 (2017-05-26)
------------------

* Fix setup.py
* Add test for Decimal trafaret field

0.1.1 (2017-05-26)
------------------

* Dirty initial version


.. _attrs: http://www.attrs.org/en/stable/
