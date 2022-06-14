GraphQL client in the terminal
==============================

Build and execute GraphQL queries in the terminal.

This project is inspired by https://graphiql-online.com.

.. image:: https://github.com/eerimoq/gqt/raw/main/docs/assets/showcase.gif

Installation
------------

.. code-block:: shell

   pip3 install gqt

It's recommended to install `bat`_ for pretty output.

Controls
--------

- Press ``h`` or ``?`` for help.

Examples
--------

Set default GraphQL endpoint:

.. code-block:: shell

   $ export GQT_ENDPOINT=https://mys-lang.org/graphql

Interactively create a query and execute it:

.. code-block:: shell

   $ gqt
   {
       "statistics": {
           "numberOfGraphqlRequests": 3
       }
   }

Repeat last query:

.. code-block:: shell

   $ gqt -r
   {
       "statistics": {
           "numberOfGraphqlRequests": 4
       }
   }

Print the query instead of executing it:

.. code-block:: shell

   $ gqt -q
   query Query {
     statistics {
       numberOfGraphqlRequests
     }
   }

YAML output:

.. code-block:: shell

   $ gqt -y
   statistics:
     numberOfGraphqlRequests: 8

Name queries:

.. code-block:: shell

   $ gqt -n stats -y
   statistics:
     numberOfGraphqlRequests: 8
   $ gqt -n time -y
   standardLibrary:
     package:
       latestRelease:
         version: 0.20.0
   $ gqt -n stats -y -r
   statistics:
     numberOfGraphqlRequests: 9
   $ gqt -n time -y -r
   standardLibrary:
     package:
       latestRelease:
         version: 0.20.0

Print the schema:

.. code-block:: shell

   $ gqt --print-schema
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

- Unions and interfaces are not implemented.

- And much more.

Ideas
-----

- Variables example:

  .. code-block::

     ╭─ Query ─ String
     │ ▼ standardLibrary
     │   ▼ package
     │     $ name: name
     │     ▼ latestRelease
     │       ■ version

  .. code-block:: shell

     $ gqt -v 'name="time"' -y
     standardLibrary:
       package:
         latestRelease:
           version: 0.20.0
     $ gqt -r -q
     query Query($name: String!) {
       standardLibrary {
         package(name: $name) {
           latestRelease {
             version
           }
         }
       }
     }

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

- Check for schema modifications when starting. Do it in the
  background and notify the user if it was modified.

  New schema fetched from the server. Use it? y/n

- Subscriptions. Probably out of scope.

.. _bat: https://github.com/sharkdp/bat
