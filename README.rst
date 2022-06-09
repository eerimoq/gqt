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

- Arguments does not work for scalar and input types.

- Unions are not implemented.

- And much more.

Ideas
-----

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

- Required arguments with default value:

  .. code-block::

     □: omit
     ■: non-null value
     $: variable

- Check for schema modifications when starting. Do it in the
  background and notify the user if it was modified.

  New schema fetched from the server. Use it? y/n

- List argument example:

  .. code-block::

     ╭─ Query
     │ ▼ item
     │   ■ kinds:
     │     [0] ■ a: foo
     │         ■ b: eq
     │         ■ c:
     │           [0] ■ a: x
     │               ■ b: y
     │           [1]
     │     [1] ■ a: bar
     │         ■ b: ne
     │         □ c:
     │     [2]

- Input example:

  .. code-block::

     ╭─ Query
     │ ▼ item
     │   ■ config:
     │     ■ unit: metric
     │     □ width:
     │   □ length
     │   □ weight

- Variables example:

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
     │ name: time
     │ kind:
     │   [0] ■ a: bar
     │       ■ b: ne
     │       □ c:
     │   [1]

- Print variables:

  .. code-block:: shell

     $ gqt -v
     {"name": "foo", "kind": [{"a": "bar", "b": "ne"}]}

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

- Subscriptions. Probably out of scope.

.. _jq: https://github.com/stedolan/jq
.. _bat: https://github.com/sharkdp/bat
