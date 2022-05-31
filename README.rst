GraphQL in the terminal
=======================

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

- Variables?

- Arguments:

  Scalars:

  .. code-block::

     □: null
     ■: not null

  Lists:

  .. code-block::

     >: null
     v: not null

  Scalar example:

  .. code-block::

     v standard_library
       v package
         ■ name*: ""             # Cannot be unselected as it cannot be null.
         □ name
       > packages

  List example:

  .. code-block::

     > kinds*:                     # Argument is null.
     v kinds*:                     # List with two elements.
       v a: "foo"
         b: "eq"
         c: "kalle"
       v a: "bar"
         b: "ne"
         c: "frolle"
       > ...
