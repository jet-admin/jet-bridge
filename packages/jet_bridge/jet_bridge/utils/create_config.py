from __future__ import unicode_literals

import os

import six
from prompt_toolkit import prompt, print_formatted_text, HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator
from sqlalchemy import create_engine

from jet_bridge import settings
from jet_bridge_base.db_types.sql import sql_build_engine_url

engines = [
    {
        'name': 'postgresql',
        'default_port': 5432
    },
    {
        'name': 'mysql',
        'default_port': 3306
    },
    {
        'name': 'oracle',
        'default_port': 1521
    },
    {
        'name': 'mssql+pyodbc',
        'default_port': 1433
    },
    {
        'name': 'bigquery'
    },
    {
        'name': 'snowflake'
    },
    {
        'name': 'cockroachdb'
    },
    {
        'name': 'awsathena+rest'
    },
    {
        'name': 'clickhouse+native'
    },
    {
        'name': 'databricks'
    },
    {
        'name': 'sqlite'
    },
    {
        'name': 'none'
    }
]


def is_not_empty(text):
    return text is not None and text.strip() != ''


def database_engine_is_valid(text):
    return text in list(map(lambda x: x['name'], engines))


def port_is_valid(text):
    try:
        int(text)
        return True
    except ValueError as e:
        return False


def is_file_exists(text):
    return os.path.exists(text) and os.path.isfile(text)


promt_messages = 0


def create_config(config_not_set):
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>'))

    if config_not_set:
        print_formatted_text(HTML('<skyblue><b>Configuration is not set</b></skyblue>'))
    else:
        print_formatted_text(HTML('<skyblue><b>Configuration</b></skyblue>'))

    print_formatted_text(HTML('<skyblue>You will be asked to enter settings</skyblue>'))
    print_formatted_text(HTML('<skyblue>and config file will be generated</skyblue>'))
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>\n'))

    # session = PromptSession()
    html_completer = WordCompleter(list(map(lambda x: x['name'], engines)))

    def promt_message(message):
        global promt_messages
        promt_messages += 1
        return HTML('{}. {}\n> '.format(promt_messages, message))

    if 'project' not in settings.USE_DEFAULT_CONFIG:
        project = prompt(
            promt_message('<green><b>Enter your project unique name</b></green>'),
            default=settings.PROJECT
        )

        print_formatted_text('')
    else:
        project = settings.PROJECT

    if 'token' not in settings.USE_DEFAULT_CONFIG:
        token = prompt(
            promt_message('<green><b>Enter your Jet Bridge token</b></green>'),
            default=settings.TOKEN
        )

        print_formatted_text('')
    else:
        token = settings.TOKEN

    if 'address' not in settings.USE_DEFAULT_CONFIG:
        address = prompt(
            promt_message('<green><b>Which host to run Jet Bridge on?</b></green>\n<i>Default is {}</i>'.format('0.0.0.0 (any IP)')),
            default=settings.ADDRESS or '0.0.0.0'
        )

        print_formatted_text('')
    else:
        address = settings.ADDRESS or '0.0.0.0'

    port = prompt(
        promt_message('<green><b>Which port to run Jet Bridge on?</b></green>\n<i>Default is {}</i>'.format('8888')),
        validator=Validator.from_callable(
            port_is_valid,
            error_message='Incorrect port',
            move_cursor_to_end=True
        ),
        default='{0}'.format(settings.PORT) if settings.PORT else '8888'
    )

    print_formatted_text('')

    database_engine = prompt(
        promt_message('<green><b>Which database do you use?</b></green>\n<i>Should be one of: {}</i>'.format(
            ', '.join(map(lambda x: x['name'], engines)))),
        validator=Validator.from_callable(
            database_engine_is_valid,
            error_message='Unknown database engine',
            move_cursor_to_end=True
        ),
        completer=html_completer,
        validate_while_typing=False,
        default=settings.DATABASE_ENGINE or ''
    )

    database_name = None
    database_host = None
    database_port = None
    database_user = None
    database_password = None
    database_extra = None

    while True:
        print_formatted_text('')

        if database_engine == 'none':
            database_host = ''
            database_port = ''
            database_name = ''
            database_user = ''
            database_password = ''

            break
        elif database_engine == 'sqlite':
            prompts = 1

            database_name = prompt(
                promt_message('<green><b>Enter your database file path</b></green>'),
                validator=Validator.from_callable(
                    is_file_exists,
                    error_message='File does not exist on given path',
                    move_cursor_to_end=True
                ),
                default=database_name or settings.DATABASE_NAME or ''
            )

            database_host = ''
            database_port = ''
            database_user = ''
            database_password = ''
        elif database_engine == 'bigquery':
            prompts = 5

            database_name = prompt(
                promt_message('<green><b>Enter your BigQuery project name</b></green>'),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='BigQuery project name is required',
                    move_cursor_to_end=True
                ),
                default=database_name or settings.DATABASE_NAME or ''
            )

            print_formatted_text('')

            database_password = prompt(
                promt_message('<green><b>Enter your service account key</b></green>'),
                default=database_password or settings.DATABASE_PASSWORD or ''
            )
        elif database_engine == 'snowflake':
            prompts = 5

            message = '<green><b>Enter your account name</b></green>'

            database_host = prompt(
                promt_message(message),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Account name is required',
                    move_cursor_to_end=True
                )
            )

            print_formatted_text('')

            database_name = prompt(
                promt_message('<green><b>Enter your database name</b></green>'),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Database name is required',
                    move_cursor_to_end=True
                ),
                default=database_name or settings.DATABASE_NAME or ''
            )

            print_formatted_text('')

            database_user = prompt(
                promt_message('<green><b>Enter your database user</b></green>'),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Database user is required',
                    move_cursor_to_end=True
                ),
                default=database_user or settings.DATABASE_USER or ''
            )

            print_formatted_text('')

            database_password = prompt(
                promt_message('<green><b>Enter your database password</b></green>'),
                default=database_password or settings.DATABASE_PASSWORD or ''
            )

            print_formatted_text('')

            warehouse_name = prompt(
                promt_message('<green><b>Enter your warehouse name</b></green>'),
                default='compute_wh'
            )

            database_extra = 'warehouse={}'.format(warehouse_name)
        else:
            prompts = 5

            default = database_host or settings.DATABASE_HOST or 'localhost'
            message = '<green><b>Enter your database host</b></green>\n<i>Default is {}</i>'.format('localhost')

            if settings.POSSIBLE_HOST:
                message += '\n<b>{}</b> should point to <b>{}</b> on Docker environment'.format(settings.POSSIBLE_HOST, 'localhost')

            database_host = prompt(
                promt_message(message),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Database host is required',
                    move_cursor_to_end=True
                ),
                default=default
            )

            print_formatted_text('')

            default_port = list(map(lambda x: six.text_type(x.get('default_port', '')), filter(
                lambda x: x['name'] == database_engine, engines
            )))[0]

            database_port = prompt(
                promt_message('<green><b>Enter your database port</b></green>'),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Database port is required',
                    move_cursor_to_end=True
                ),
                default=database_port or '{0}'.format(settings.DATABASE_PORT) if settings.DATABASE_PORT else '{0}'.format(default_port)
            )

            print_formatted_text('')

            database_name = prompt(
                promt_message('<green><b>Enter your database name</b></green>'),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Database name is required',
                    move_cursor_to_end=True
                ),
                default=database_name or settings.DATABASE_NAME or ''
            )

            print_formatted_text('')

            database_user = prompt(
                promt_message('<green><b>Enter your database user</b></green>'),
                validator=Validator.from_callable(
                    is_not_empty,
                    error_message='Database user is required',
                    move_cursor_to_end=True
                ),
                default=database_user or settings.DATABASE_USER or ''
            )

            print_formatted_text('')

            database_password = prompt(
                promt_message('<green><b>Enter your database password</b></green>'),
                default=database_password or settings.DATABASE_PASSWORD or ''
            )

        engine_url = sql_build_engine_url({
            'engine': database_engine,
            'host': database_host,
            'port': database_port,
            'name': database_name,
            'user': database_user,
            'password': database_password,
            'extra': database_extra
        })

        if not engine_url:
            continue

        engine = create_engine(engine_url)

        try:
            connection = engine.connect()
            connection.close()
        except Exception as e:
            global promt_messages
            print_formatted_text('')
            print_formatted_text(HTML('<red><b>Connection failed:</b></red>'))
            print_formatted_text(HTML('<red>{}</red>'.format(e)))
            print_formatted_text('')
            print_formatted_text(HTML('<skyblue><b>Please try again</b></skyblue>'))
            promt_messages -= prompts
            continue

        print_formatted_text('')
        print_formatted_text(HTML('<skyblue><b>Database connected successfully!</b></skyblue>'))
        print_formatted_text('')

        break

    if 'config' not in settings.USE_DEFAULT_CONFIG:
        print_formatted_text('')

        config = prompt(
            promt_message('<green><b>Where to store config file?</b></green>\nDefault is jet.conf inside current working directory\n[{}]'.format(os.path.abspath(settings.DEFAULT_CONFIG_PATH))),
            default=settings.CONFIG or '{0}'.format(settings.DEFAULT_CONFIG_PATH)
        )
    else:
        config = settings.CONFIG or '{0}'.format(settings.DEFAULT_CONFIG_PATH)

    config_content = {
        'ADDRESS': address,
        'PORT': port,
        'CONFIG': config,
        'PROJECT': project,
        'TOKEN': token,
        'DATABASE_ENGINE': database_engine,
        'DATABASE_HOST': database_host,
        'DATABASE_PORT': database_port,
        'DATABASE_NAME': database_name,
        'DATABASE_USER': database_user,
        'DATABASE_PASSWORD': database_password
    }

    if settings.ENVIRONMENT:
        config_content['ENVIRONMENT'] = settings.ENVIRONMENT

    if settings.WEB_BASE_URL and settings.WEB_BASE_URL != settings.DEFAULT_WEB_BASE_URL:
        config_content['WEB_BASE_URL'] = settings.WEB_BASE_URL

    if settings.API_BASE_URL and settings.API_BASE_URL != settings.DEFAULT_API_BASE_URL:
        config_content['API_BASE_URL'] = settings.API_BASE_URL

    try:
        os.makedirs(os.path.dirname(config))
    except OSError:
        pass

    with open(config, 'w') as f:
        f.write('[JET]\n')
        for key, value in config_content.items():
            f.write('{}={}\n'.format(key, value))

    print_formatted_text('')
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>'))
    print_formatted_text(HTML('<skyblue><b>Configuration file is created at:</b></skyblue>'))
    print_formatted_text(HTML('<skyblue>{}</skyblue>'.format(os.path.abspath(config))))
    print_formatted_text('')
    print_formatted_text(HTML('<skyblue>You can now start <b>Jet Bridge</b></skyblue>'))
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>\n'))
