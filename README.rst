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
   {statistics {numberOfGraphqlRequests}}

Use `jq`_ for colors and extracting field values:

.. code-block:: shell

   $ gqt | jq
   {
     "statistics": {
       "numberOfGraphqlRequests": 5
     }
   }
   $ gqt | jq .statistics.numberOfGraphqlRequests
   6

Alternatively use and `bat`_ for colors:

.. code-block:: shell

   $ gqt | bat -l json
   ───────┬────────────────────────────────────────────
          │ STDIN
   ───────┼────────────────────────────────────────────
      1   │ {
      2   │    "statistics" : {
      3   │       "numberOfGraphqlRequests" : 7
      4   │    }
      5   │ }
   ───────┴────────────────────────────────────────────

Use YAML output and `bat`_ for colors:

.. code-block:: shell

   $ gqt -y | bat -l yaml
   ───────┬────────────────────────────────────────────
          │ STDIN
   ───────┼────────────────────────────────────────────
      1   │ statistics:
      2   │   numberOfGraphqlRequests: 8
   ───────┴────────────────────────────────────────────

Print the schema:

.. code-block:: shell

   $ gqt --print-schema | bat -l graphql
   ───────┬────────────────────────────────────────────
          │ STDIN
   ───────┼────────────────────────────────────────────
      1   │ type Query {
      2   │   standardLibrary: StandardLibrary!
      3   │   statistics: Statistics!
      4   │   activities: [Activity!]!
      5   │ }
      6   │
      7   │ type StandardLibrary {
      8   │   package(name: String!): Package!
      9   │   packages: [Package!]
     10   │   numberOfPackages: Int
     11   │   numberOfDownloads: Int
     12   │ }
     ...

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
     │ ▼ standardLibrary
     │   ▼ package
     │     $ name: name
     │     ■ id: 5
     │     $ kind: kind
     │     □ name
     │   □ numberOfDownloads
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
