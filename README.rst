GraphQL in the terminal
=======================

This project is inspired by https://graphiql-online.com.

.. image:: https://github.com/eerimoq/gqt/raw/main/docs/assets/showcase.gif

Installation
------------

.. code-block:: shell

   $ pip3 install gqt

Usage
-----

Set default GraphQL end-point URL:

.. code-block:: shell

   $ export GQT_URL=https://mys-lang.org/graphql

Interactively create a query and execute it:

.. code-block:: shell

   $ gqt
   {
       "statistics": {
           "start_date_time": "2022-05-29 20:54:48",
           "number_of_graphql_requests": 234
       }
   }

Repeat last query:

.. code-block:: shell

   $ gqt -r
   {
       "statistics": {
           "start_date_time": "2022-05-29 20:54:48",
           "number_of_graphql_requests": 234
       }
   }

Print the query instead of executing it:

.. code-block:: shell

   $ gqt -q
   {"query":"{statistics {start_date_time number_of_graphql_requests}}"}

Use ``jq`` for colors (not seen below) and extracting field values:

.. code-block:: shell

   $ gqt | jq
   {
     "statistics": {
       "start_date_time": "2022-05-29 20:54:48",
       "number_of_graphql_requests": 235
     }
   }
   $ gqt | jq .statistics.number_of_graphql_requests
   236

Ideas
-----

- Print built query instead of executing it.

- Contols:

  - Use ``/`` to fuzzy find field.

- Arguments and variables:

  .. code-block::

     □: null
     ■: not null
     $: variable

  Scalar example:

  .. code-block::

     ╭─ Query
     │ ▼ standard_library
     │   ▼ package
     │     ■ name: ""
     │     □ name
     │   ▶ packages

  List example:

  .. code-block::

     ╭─ Query
     │ ▼ item
     │   □ kinds:
     │   ■ kinds2:
     │     [0] ■ a: "foo"
     │         ■ b: "eq"
     │         ■ c:
     │           [0] ■ a: "x"
     │               ■ b: "y"
     │           [1]
     │     [1] ■ a: "bar"
     │         ■ b: "ne"
     │         □ c:
     │     [2]

  Variables example:

  .. code-block::

     ╭─ Query
     │ ▼ standard_library
     │   ▼ package
     │     $ name: name
     │     ■ id: 5
     │     $ kind: kind
     │     □ name
     │   □ number_of_downloads
     │ ▶ statistics

     ╭─ Variables
     │ name: "foo"
     │ kind:
     │   [0] ■ a: "foo"
     │       ■ b: "eq"
     │       ■ c:
     │         [0] ■ a: "x"
     │             ■ b: "y"
     │         [1]
     │   [1] ■ a: "bar"
     │       ■ b: "ne"
     │       □ c:
     │   [2]
