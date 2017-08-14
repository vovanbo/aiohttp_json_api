.. highlight:: shell

============
Installation
============


Stable release
--------------

To install aiohttp JSON API, run this command in your terminal:

.. code-block:: console

    $ pip install aiohttp_json_api

This is the preferred method to install aiohttp JSON API, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for aiohttp JSON API can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/vovanbo/aiohttp_json_api

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/vovanbo/aiohttp_json_api/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/vovanbo/aiohttp_json_api
.. _tarball: https://github.com/vovanbo/aiohttp_json_api/tarball/master


Default setup of resources, routes and handlers
-----------------------------------------------

=====================  ======  =========================================  ======================================================
Resource name          Method  Route                                      Handler
=====================  ======  =========================================  ======================================================
jsonapi.collection     GET     ``/{type}``                                :func:`~aiohttp_json_api.handlers.get_collection`
jsonapi.collection     POST    ``/{type}``                                :func:`~aiohttp_json_api.handlers.post_resource`
jsonapi.resource       GET     ``/{type}/{id}``                           :func:`~aiohttp_json_api.handlers.get_resource`
jsonapi.resource       PATCH   ``/{type}/{id}``                           :func:`~aiohttp_json_api.handlers.patch_resource`
jsonapi.resource       DELETE  ``/{type}/{id}``                           :func:`~aiohttp_json_api.handlers.delete_resource`
jsonapi.relationships  GET     ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.get_relationship`
jsonapi.relationships  POST    ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.post_relationship`
jsonapi.relationships  PATCH   ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.patch_relationship`
jsonapi.relationships  DELETE  ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.delete_relationship`
jsonapi.related        GET     ``/{type}/{id}/{relation}``                :func:`~aiohttp_json_api.handlers.get_related`
=====================  ======  =========================================  ======================================================

