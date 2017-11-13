=======
History
=======

0.30.0 (2017-11-13)
-------------------

* Improve performance of URL resolving in Link field (with `cachetools`_)
* Upgrade requirements


0.29.2 (2017-11-02)
-------------------

* Documentation improvements


0.29.1 (2017-11-02)
-------------------

* Update README
* Upgrade requirements


0.29.0 (2017-11-02)
-------------------

* Simple example of usage is added
* Fix bug in handler of relationship query


0.28.3 (2017-11-02)
-------------------

* Fix bug with wrong read-only field error
* Don’t require setup ID field in Schema to update a resource


0.28.2 (2017-11-01)
-------------------

* Add multidict_ to requirements and to README


0.28.1 (2017-10-31)
-------------------

* Fix small bug with wrong empty sorting in RequestContext


0.28.0 (2017-10-31)
-------------------

* Add support for customizable inflection of fields from query string.
* Convert static methods of RequestContext to class methods
* Update docs of RequestContext methods


0.27.1 (2017-10-31)
-------------------

* Fix packaging of ABCs and compats


0.27.0 (2017-10-31)
-------------------

* Abstract base classes refactoring (separate Field and Schema ABCs)
* Fix bug with compound documents in case models has no property “resource_id”
* Remove buggy helper to check subclass of any instance
* Decompose setup application method to increase readability
* Properly error raised in jsonapi_handler decorator
* Use one field instead of two to check what type of relation have the field


0.26.0 (2017-10-30)
-------------------

* Properly use abstract base classes. Inherit SchemaABC from ABC.
* Rename resource validation methods *(backward incompatible)*


0.25.0 (2017-10-18)
-------------------

* Add Tuple field
* Fix bug with List field items enumeration
* Fix wrong conversion of Decimal field to string on deserialization
* Add yarl_ (>=0.13) to requirements


0.24.1 (2017-10-12)
-------------------

* Add support for length range specifying for List field


0.24.0 (2017-10-04)
-------------------

* Convert document render utility to async coroutine *(backward incompatible)*
* Rename Error class property "json" to "as_dict" to clarify


0.23.0 (2017-10-03)
-------------------

* Use MultiDict for request context filters and FilterRule tuple *(backward incompatible)*
* Debug info on request context creation


0.22.2 (2017-09-27)
-------------------

* Add support for nullable List field


0.22.1 (2017-09-25)
-------------------

* Fix bug with wrong exit from compound documents fetch utility ("return" instead of "break")


0.22.0 (2017-09-22)
-------------------

* Remove recursive fetching of compound documents. Replace it with simple loop.


0.21.2 (2017-09-22)
-------------------

* Fix bug with fetching compound documents when query parameter "include" contains the same relation twice and more.


0.21.1 (2017-09-19)
-------------------

* Fix bug with non-underscored relation name in relationship handlers


0.21.0 (2017-09-19)
-------------------

* Add support for field names conversion passed to "include" request context
* Update development requirements


0.20.2 (2017-08-30)
-------------------

* Avoid assertion in Registry ensure identifier method
* Make Schema getter of object id static
* Avoid to filter out empty fields of rendered documents (less memory and faster)
* Get id field of schema more safely in URI resource ID validator


0.20.1 (2017-08-15)
-------------------

* Add support for load only fields (like a Marshmallow)


0.20.0 (2017-08-14)
-------------------

* Asynchronous validators support
* Routes namespace can be customized
* Relative links support


0.19.1 (2017-08-10)
-------------------

* Improve serialization result default keys creation


0.19.0 (2017-08-10)
-------------------

* Refactor schema serializer to fix bug with no resource link in result
* Clean-up validation of expected ID in pre-validaiton of resource
* Use status property of ErrorList in error middleware to return HTTP status
* Remove default getter from Link field, because it doesn't used anymore


0.18.1 (2017-08-09)
-------------------

* Migrate to trafaret >= 0.11.0
* Fix requirement of trafaret to version greater than 0.11.0


0.18.0 (2017-08-09)
-------------------

* Properly handle missing values in deserialization and validation


0.17.1 (2017-07-31)
-------------------

* Add support for validation of Relationships ID field


0.17.0 (2017-07-28)
-------------------

* Normalize resource_id parameter usage in all mutation methods.
* Add fetch_resource schema coroutine to receive resource instance by ID.
* Add separate method for mapping deserialized data to schema.
* Context is required parameter for deserialization schema method.
* Move docs to ABC schema.
* Properly handle allow_none parameter for UUID field


0.16.2 (2017-07-24)
-------------------

* Fix arguments passed to validators


0.16.1 (2017-07-24)
-------------------

* Pass context to value setter in update methods


0.16.0 (2017-07-22)
-------------------

* Strict member names and type checking to conform JSON API requirements (routes and schema level). See also: http://jsonapi.org/format/#document-member-names
* Strict check for overrides of handlers
* Improve debug logging


0.15.2 (2017-07-21)
-------------------

* Initialize default relationships links in meta-class, to avoid bug with empty names of relationships fields


0.15.1 (2017-07-19)
-------------------

* Rename resource ID parameter of query_resource schema' method.


0.15.0 (2017-07-18)
-------------------

* Pagination is initialized from request by default. Remove separate class method of BasePagination to initialize pagination instance
* Improve value validation error for absent fields
* Improve validation error of string field with choices


0.14.0 (2017-07-13)
-------------------

* Customisable JSON API handlers support
* DRY in handlers
* Move context builder from middleware to jsonapi_handler decorator
* Request context receive optional resource_type now


0.13.0 (2017-07-12)
-------------------

* Revert back to asynchronous setters, because it's used in update relationships and it might want to query DB, for example


0.12.0 (2017-07-12)
-------------------

* Base Registry class from UserDict, so Registry is a dict with ensure_identifier method.
* More strict typing checks on setup.


0.11.1 (2017-07-11)
-------------------

* Fix bug with mutation not cloned resource in method for delete relationship
* Require JSON API content type on delete relationships


0.11.0 (2017-07-11)
-------------------

* Method for update return original and updated resource as result. Updated resource is created via deepcopy. It will be useful to determine returned HTTP status
* Fix bug with enumeration (choices) in String field
* Fix bug with context event setup for OPTIONS, HEAD and another request methods not used in JSON API


0.10.0 (2017-07-10)
-------------------

* Mass refactoring of schema, fields, validation and decorators
* Generic approach to setup Schema decorators is used (inspired by Marshmallow)
* Fields are used only for encode/decode now (with pre/post validation). Additional validators for fields must be created on schema level
* Custom JSON encoder with support JSONPointer serialization
* Remove boltons from requirements
* No more remap input data dictionary with key names to underscores conversion.
* Add helpers "first" and "make_sentinel" (cherry-picked from boltons)
* Fix enumeration (choices) support in String field


0.9.3 (2017-07-06)
------------------

* Setup content-type validation on mutation API methods (application/vnd.api+json is required)
* Properly get and encode relationships fields
* Update docs and typing for ensure_identifier Registry's method


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
.. _yarl: https://yarl.readthedocs.io
.. _multidict: http://multidict.readthedocs.io/en/stable/
.. _cachetools: https://github.com/tkem/cachetools
