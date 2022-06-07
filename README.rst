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

- Navigate with arrow keys.

- Select fields with <Space>.

- Toggle between argument selection and its value with <Tab>.

- End with <Enter>.

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
   query Query {statistics {numberOfGraphqlRequests}}

YAML output:

.. code-block:: shell

   $ gqt -y
   statistics:
     numberOfGraphqlRequests: 8

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

- Arguments does not work very well.

- Fragments and unions are not implemented.

- Mutations and subscriptions are not implemented.

- And much more.

Ideas
-----

- Show GraphQL API documentation.

- Check for schema modifications when starting. Do it in the
  background and notify the user if it was modified.

  New schema fetched from the server. Use it? y/n

- Mutations?

- Subscriptions?

- Arguments and variables:

  For required arguments with default value:

  .. code-block::

     □: omit
     ■: non-null value
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

  Input example:

  .. code-block::

     ╭─ Query
     │ ▼ item
     │   ■ config:
     │     ■ unit: "metric"
     │     □ width:
     │   □ length
     │   □ weight

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

- Leaves with arguments:

  .. code-block::

     type Query {
         foo(id: Int, name: String): String
     }

     Unselected:

     ╭─ Query
     │ □ foo

     Selected:

     ╭─ Query
     │ ■ foo
     │   ■ id: 5
     │   □ name:

.. _jq: https://github.com/stedolan/jq
.. _bat: https://github.com/sharkdp/bat
