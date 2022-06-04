GraphQL client in the terminal
==============================

This project is inspired by https://graphiql-online.com.

.. image:: https://github.com/eerimoq/gqt/raw/main/docs/assets/showcase.gif

Installation
------------

.. code-block:: shell

   $ pip3 install gqt

Usage
-----

Set default GraphQL endpoint URL:

.. code-block:: shell

   $ export GQT_ENDPOINT=https://mys-lang.org/graphql

Interactively create a query and execute it:

.. code-block:: shell

   $ gqt
   {"statistics": {"number_of_graphql_requests": 234}}

Repeat last query:

.. code-block:: shell

   $ gqt -r
   {"statistics": {"number_of_graphql_requests": 235}}

Print the query instead of executing it:

.. code-block:: shell

   $ gqt -q
   {"query":"{statistics {number_of_graphql_requests}}"}

Use `jq`_ for indentation, colors and extracting field values:

.. code-block:: shell

   $ gqt | jq
   {
     "statistics": {
       "number_of_graphql_requests": 236
     }
   }
   $ gqt | jq .statistics.number_of_graphql_requests
   237

Alternatively use ``json_pp`` and `bat`_ for indentation and colors:

.. code-block:: shell

   $ gqt | json_pp | bat -l json
   ───────┬──────────────────────────────────────────────────────────────
          │ STDIN
   ───────┼──────────────────────────────────────────────────────────────
      1   │ {
      2   │    "statistics" : {
      3   │       "number_of_graphql_requests" : 238
      4   │    }
      5   │ }
   ───────┴──────────────────────────────────────────────────────────────

Use YAML output and `bat`_ for indentation and colors:

.. code-block:: shell

   $ gqt -y | bat -l yaml
   ───────┬──────────────────────────────────────────────────────────────
          │ STDIN
   ───────┼──────────────────────────────────────────────────────────────
      1   │ statistics:
      2   │   number_of_graphql_requests: 239
   ───────┴──────────────────────────────────────────────────────────────

Known issues
------------

- Arguments does not work very well.

- Scrolling.

Ideas
-----

- Mutations?

- Subscriptions?

- Arguments and variables:

  .. code-block::

     ■: not null
     □: null
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
     │   [0] ■ a: "bar"
     │       ■ b: "ne"
     │       □ c:
     │   [1]

  Print the variables:

  .. code-block:: shell

     $ gqt -v
     {"name": "foo", "kind": [{"a": "bar", "b": "ne"}]}

.. _jq: https://github.com/stedolan/jq
.. _bat: https://github.com/sharkdp/bat
