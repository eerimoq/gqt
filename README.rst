GraphQL client in the terminal
==============================

Build and execute GraphQL queries in the terminal.

This project is inspired by https://graphiql-online.com.

.. image:: https://github.com/eerimoq/gqt/raw/main/docs/assets/showcase.gif

Installation
------------

.. code-block::

   pip3 install gqt

It's recommended to install `bat`_ for pretty output.

Controls
--------

- Press ``h`` or ``?`` for help.

Examples
--------

Set default GraphQL endpoint:

.. code-block::

   export GQT_ENDPOINT=https://mys-lang.org/graphql

Interactively create a query and execute it:

.. code-block::

   gqt

.. code-block:: json

   {
       "statistics": {
           "numberOfGraphqlRequests": 3
       }
   }

Repeat last query:

.. code-block::

   gqt -r

.. code-block:: json

   {
       "statistics": {
           "numberOfGraphqlRequests": 4
       }
   }

Print the query instead of executing it:

.. code-block::

   gqt -q

.. code-block:: graphql

   query Query {
     statistics {
       numberOfGraphqlRequests
     }
   }

YAML output:

.. code-block::

   gqt -y

.. code-block:: yaml

   statistics:
     numberOfGraphqlRequests: 8

Name queries:

.. code-block::

   gqt -n stats -y

.. code-block:: yaml

   statistics:
     numberOfGraphqlRequests: 8

.. code-block::

   gqt -n time -y

.. code-block:: yaml

   standardLibrary:
     package:
       latestRelease:
         version: 0.20.0

.. code-block::

   gqt -n stats -y -r

.. code-block:: yaml

   statistics:
     numberOfGraphqlRequests: 9

.. code-block::

   gqt -n time -y -r

.. code-block:: yaml

   standardLibrary:
     package:
       latestRelease:
         version: 0.20.0

Make arguments variables by pressing ``v`` or ``$`` and give them as
``-v <name>=<value>`` on the command line:

.. code-block::

   gqt -v name=time -y

.. code-block:: yaml

   standardLibrary:
     package:
       latestRelease:
         version: 0.20.0

.. code-block::

   gqt -r -q

.. code-block:: graphql

   query Query($name: String!) {
     standardLibrary {
       package(name: $name) {
         latestRelease {
           version
         }
       }
     }
   }

Print the schema:

.. code-block::

   gqt --print-schema

.. code-block:: graphql

   type Query {
     standardLibrary: StandardLibrary!
     statistics: Statistics!
     activities: [Activity!]!
   }

   type StandardLibrary {
     package(name: String!): Package!
     packages: [Package!]
     numberOfPackages: Int
     numberOfDownloads: Int
   }
   ...

Known issues
------------

- Unions are not implemented.

- There is one query cache per ``gqt`` version. Would be nice to keep
  the cache after upgrading ``gqt``.

Ideas
-----

- Unions:

  Always query ``__typename``.

  .. code-block::

     union SearchResult = Book | Author

     type Book {
       title: String!
     }

     type Author {
       name: String!
     }

     type Query {
       search(contains: String): [SearchResult!]
     }

     Unselected:

     ╭─ Query
     │ ▶ search

     Selected:

     ╭─ Query
     │ ▼ search
     │   ▶ Book
     │     ■ title
     │   ▶ Author
     │     ■ name

- Alias?

  - Press ``a`` to create an alias.

  - Press ``d`` to delete an alias.

  ``smallPicture`` and ``mediumPicture`` are aliases of ``picture``.

  .. code-block::

     ╭─ Query
     │ ▶ Book
     │   ▶ picture
     │   ▼ smallPicture: picture
     │     ■ width: 320
     │     ■ height: 240
     │   ▼ mediumPicture: picture
     │     ■ width: 800
     │     ■ height: 600

- Keep valid parts of any existing query when reloading the schema.

- Cache across updates.

  - Save introspection response.

  - Save last query.

  - Save cursor and possibly other state.

  .. code-block::

     -- ~/.cache/gqt/cache/generic/
        +-- <endpoint 1>
            +-- schema.json
            +-- query.graphql
            +-- state.json
            +-- query_names/
                +-- stats/
                    +-- schema.json
                    +-- query.graphql
                    +-- state.json

- Optionally give schema path on command line. For endpoints that does
  not support schema introspection.

.. _bat: https://github.com/sharkdp/bat
