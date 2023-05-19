import argparse
import json
import logging
import os
import shutil
import subprocess
import sys

import requests
import yaml
from graphql import build_client_schema
from graphql import print_schema
from graphql.language import parse
from graphql.language import print_ast
from tabulate import tabulate

from .database import clear_database
from .database import get_queries
from .database import read_tree_from_database
from .endpoint import create_query
from .endpoint import fetch_schema
from .endpoint import post
from .query_builder import QuitError
from .query_builder import query_builder
from .version import __version__


def default_endpoint():
    return os.environ.get('GQT_ENDPOINT', 'https://mys-lang.org/graphql')


def last_query(endpoint, query_name):
    try:
        return read_tree_from_database(endpoint, query_name)
    except Exception:
        if query_name is None:
            message = f"No query found for endpoint '{endpoint}'."
        else:
            message = f"No query '{query_name}' found for endpoint '{endpoint}'."

        sys.exit(message)


def execute_query(endpoint, query, headers, verify):
    response = post(endpoint, query, headers, verify).json()
    errors = response.get('errors')

    if errors is not None:
        for error in errors:
            print('error:', error['message'], file=sys.stderr)

        sys.exit(1)

    return response['data']


def style_response(response, format_yaml):
    json_data = json.dumps(response, ensure_ascii=False, indent=4)

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
{headers}\
     '{endpoint}' \\
     -d '{query}'\
'''


def show(data, language, color=False, to_stderr=False):
    if 'GQT_NO_BAT' not in os.environ and shutil.which('bat'):
        data += '\n'
        command = f'bat -p -l {language}'

        if color:
            command += ' --color always'

        if to_stderr:
            command += ' 1>&2'

        subprocess.run(command, input=data, shell=True, text=True)
    elif to_stderr:
        print(data, file=sys.stderr)
    else:
        print(data)


def make_headers(headers_list):
    if not headers_list:
        return None

    headers = {}

    for header in headers_list:
        key, _, value = header.partition(':')
        headers[key] = value.strip()

    return headers


def make_curl_headers(headers_list):
    if not headers_list:
        return ''

    return '\n'.join([
        f"     -H '{header}' \\"
        for header in headers_list
    ]) + '\n'


def create_variables(variables):
    result = {}

    for variable in variables:
        name, split, value = variable.partition('=')

        if not name or split != '=' or not value:
            sys.exit(f"Invalid variable '{variable}'.")

        try:
            value = json.loads(value)
        except Exception:
            try:
                value = json.loads(f'"{value}"')
            except Exception:
                sys.exit(f"Invalid variable '{variable}'.")

        result[name] = value

    return result


def list_queries():
    print(tabulate(get_queries(), ('Endpoint', 'Query name')))


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
    parser.add_argument('-n', '--query-name',
                        help='Query name.')
    parser.add_argument(
        '-v', '--variable',
        action='append',
        default=[],
        help='A variable given as <name>=<value>. May be given multiple times.')
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
    parser.add_argument('-l', '--list-queries',
                        action='store_true',
                        help='List all queries and exit.')
    parser.add_argument('--clear',
                        action='store_true',
                        help='Clear the database and exit.')
    parser.add_argument('--no-verify',
                        action='store_true',
                        help='No SSL verification.')
    parser.add_argument('-H', '--header',
                        action='append',
                        help='Extra HTTP header. May be given multiple times.')
    parser.add_argument('--color',
                        action='store_true',
                        help='Force color output.')
    args = parser.parse_args()

    try:
        headers = make_headers(args.header)
    except Exception:
        sys.exit('Bad header given.')

    if args.clear:
        clear_database()
        return

    if args.list_queries:
        list_queries()
        return

    logging.captureWarnings(True)
    verify = not args.no_verify

    try:
        if args.print_schema:
            schema = print_schema(
                build_client_schema(
                    fetch_schema(args.endpoint, headers, verify)))
            show(schema, 'graphql', args.color)
        else:
            variables = create_variables(args.variable)

            if args.repeat:
                query = last_query(args.endpoint, args.query_name)
            else:
                query = query_builder(args.endpoint,
                                      args.query_name,
                                      headers,
                                      verify,
                                      list(variables.keys()))

            query = query.query()

            if args.print_query:
                print('Query:')
                show(print_ast(parse(str(query))), 'graphql', args.color)
                print()
                print('Variables:')
                show(json.dumps(variables, indent=4), 'json', args.color)
            elif args.print_curl:
                query = json.dumps(create_query(query, variables))
                print(CURL_COMMAND.format(endpoint=args.endpoint,
                                          query=query,
                                          headers=make_curl_headers(args.header)))
            else:
                response = execute_query(args.endpoint,
                                         create_query(query, variables),
                                         headers,
                                         verify)
                response = style_response(response, args.yaml)

                if args.yaml:
                    show(response, 'yaml', args.color)
                else:
                    show(response, 'json', args.color)
    except KeyboardInterrupt:
        sys.exit(1)
    except QuitError:
        sys.exit(0)
    except SystemExit:
        raise
    except requests.exceptions.HTTPError as error:
        try:
            data = json.dumps(error.response.json(),
                              ensure_ascii=False,
                              indent=4)
        except Exception:
            sys.stderr.buffer.write(error.response.content.strip() + b'\n')
        else:
            show(data, 'json', args.color, True)

        sys.exit(f'error: {error}')
    except BaseException as error:
        sys.exit(f'error: {error}')
