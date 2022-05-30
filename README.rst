GraphQL in the terminal
=======================

.. image:: docs/assets/showcase.gif

Installation
------------

.. code-block:: text

   pip3 install gqt

Usage
-----

Interactively create a query and execute it:

.. code-block:: text

   $ gqt https://mys-lang.org/graphql
   {
       "statistics": {
           "start_date_time": "2022-05-29 20:54:48",
           "number_of_graphql_requests": 234
       }
   }

Repeat last query:

.. code-block:: text

   $ gqt -r https://mys-lang.org/graphql
   {
       "statistics": {
           "start_date_time": "2022-05-29 20:54:48",
           "number_of_graphql_requests": 234
       }
   }

Print the query instead of executing it:

.. code-block:: text

   $ gqt -q https://mys-lang.org/graphql
   {"query":"{statistics {start_date_time number_of_graphql_requests}}"}

Use ``jq`` for colors (not seen below) and extracting field values:

.. code-block:: text

   $ gqt https://mys-lang.org/graphql | jq
   {
     "statistics": {
       "start_date_time": "2022-05-29 20:54:48",
       "number_of_graphql_requests": 235
     }
   }
   $ gqt https://mys-lang.org/graphql | jq .statistics.number_of_graphql_requests
   236

Ideas
-----

- Print built query instead of executing it.

- Contols:

  - Use ``/`` to fuzzy find field.

- Variables?
