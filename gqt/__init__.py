import argparse
import json
import logging
import os
import shutil
import subprocess
import sys

import yaml
from graphql import build_client_schema
from graphql import print_schema

from .cache import CACHE_PATH
from .cache import read_tree_from_cache
from .query_builder import fetch_schema
from .query_builder import post
from .query_builder import query_builder
from .version import __version__


def default_endpoint():
    return os.environ.get('GQT_ENDPOINT', 'https://mys-lang.org/graphql')


def create_query(query):
    return {"query": query}


def last_query(endpoint):
    try:
        return read_tree_from_cache(endpoint)
    except Exception:
        sys.exit('No cached query found.')


def execute_query(endpoint, query, version, format_yaml):
    json_response = post(endpoint, query, version).json()

    if 'errors' in json_response:
        sys.exit(json_response['errors'])

    json_data = json.dumps(json_response['data'], ensure_ascii=False, indent=4)

    if format_yaml:
        return yaml.dump(yaml.load(json_data, Loader=yaml.Loader),
                         allow_unicode=True,
                         sort_keys=False,
                         Dumper=yaml.Dumper).strip()
    else:
        return json_data


CURL_COMMAND = '''\
curl -X POST \\
     -H 'content-type: application/json' \\
     '{endpoint}' \\
     -d '{query}'\
'''


def show(data, language):
    if 'GQT_NO_BAT' not in os.environ and shutil.which('bat'):
        data += '\n'
        subprocess.run(['bat', '-p', '-l', language], input=data, text=True)
    else:
        print(data)


def main():
    parser = argparse.ArgumentParser(
        description='Set GQT_NO_BAT to disable using bat for styling.')
    parser.add_argument('--version',
                        action='version',
                        version=__version__,
                        help='Print version information and exit.')
    parser.add_argument(
        '-e', '--endpoint',
        default=default_endpoint(),
        help=('GraphQL endpoint (default: %(default)s). Set environment variable '
              'GQT_ENDPOINT to override default value.'))
    parser.add_argument('-r', '--repeat',
                        action='store_true',
                        help='Repeat last query.')
    parser.add_argument('-y', '--yaml',
                        action='store_true',
                        help='Print the response as YAML instead of JSON.')
    parser.add_argument('-q', '--print-query',
                        action='store_true',
                        help='Print the query instead of executing it.')
    parser.add_argument('-c', '--print-curl',
                        action='store_true',
                        help='Print the cURL command instead of executing it.')
    parser.add_argument('-p', '--print-schema',
                        action='store_true',
                        help='Print the schema.')
    parser.add_argument('-C', '--clear-cache',
                        action='store_true',
                        help='Clear the cache and exit.')
    parser.add_argument('--no-verify',
                        action='store_true',
                        help='No SSL verification.')
    args = parser.parse_args()

    CACHE_PATH.mkdir(exist_ok=True, parents=True)

    if args.clear_cache:
        shutil.rmtree(CACHE_PATH)
        return

    logging.captureWarnings(True)
    verify = not args.no_verify

    try:
        if args.print_schema:
            schema = print_schema(
                build_client_schema(
                    fetch_schema(args.endpoint, verify)))
            show(schema, 'graphql')
        else:
            if args.repeat:
                query = last_query(args.endpoint)
            else:
                query = query_builder(args.endpoint, verify)

            query = query.query()

            if args.print_query:
                show(str(query), 'graphql')
            elif args.print_curl:
                query = json.dumps(create_query(query))
                print(CURL_COMMAND.format(endpoint=args.endpoint, query=query))
            else:
                data = execute_query(args.endpoint,
                                     create_query(query),
                                     verify,
                                     args.yaml)

                if args.yaml:
                    show(data, 'yaml')
                else:
                    show(data, 'json')
    except KeyboardInterrupt:
        sys.exit(1)
    except BaseException as error:
        sys.exit(f'error: {error}')
