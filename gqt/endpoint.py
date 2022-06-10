import sys

import requests
from graphql import get_introspection_query


def fetch_schema(endpoint, verify):
    response = post(endpoint, {"query": get_introspection_query()}, verify)
    response = response.json()

    if 'errors' in response:
        sys.exit(response['errors'])

    return response['data']


def post(endpoint, query, verify):
    response = requests.post(endpoint, json=query, verify=verify)

    if response.status_code != 200:
        print(response.text, file=sys.stderr)
        response.raise_for_status()

    return response
