import sys

import requests
from graphql import get_introspection_query


def fetch_schema(endpoint, headers, verify):
    response = post(endpoint,
                    {'query': get_introspection_query()},
                    headers,
                    verify)
    response = response.json()

    if 'errors' in response:
        sys.exit(response['errors'])

    return response['data']


def post(endpoint, query, headers, verify):
    response = requests.post(endpoint,
                             json=query,
                             headers=headers,
                             verify=verify)
    response.raise_for_status()

    return response


def create_query(query, variables):
    query = {'query': query}

    if variables:
        query['variables'] = variables

    return query
