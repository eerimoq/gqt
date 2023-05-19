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

Print the query (and variables) instead of executing it:

.. code-block::

   gqt -q

.. code-block:: graphql

   Query:
   query Query {
     statistics {
       numberOfGraphqlRequests
     }
   }

   Variables:
   {}

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

List queries:

.. code-block::

   gqt -l

.. code-block::

   Endpoint                      Query name
   ----------------------------  ------------
   https://mys-lang.org/graphql  <default>
   https://mys-lang.org/graphql  time
   https://mys-lang.org/graphql  stats

Make arguments variables by pressing ``v`` and give them as ``-v
<name>=<value>`` on the command line:

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

Enpoint option and bearer token in HTTP auth header:

.. code-block::

   gqt -e https://api.github.com/graphql -H "Authorization: bearer ghp_<value>"

Ideas
-----

- Press ``c`` for compact view, hiding fields that are not selected.

- Search:

  Press ``/`` to search for visible fields. Press ``<Up>`` and
  ``<Down>`` to move to the previous and next search hit. Highlight
  all hits. Press ``<Enter>`` to end the search and move the cursor to
  the current hit. Press ``<Esc>`` to abort the search and restore the
  cursor to its pre-search position. Show number of hits.

  .. code-block::

     ╭─ Query
     │ ▼ search
     │   ▶ Book
     │     ■ title
     │   ▶ Author
     │     ■ name
     │ ▶ film
     │ ▶ films

     /fil                                                1 of 2 matches

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

- Optionally give schema path on command line. For endpoints that does
  not support schema introspection.

.. _bat: https://github.com/sharkdp/bat
