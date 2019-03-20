import os

from prompt_toolkit import prompt, print_formatted_text, HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator

from jet_bridge import settings


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
        'name': 'mssql',
        'default_port': 1433
    },
    {
        'name': 'sqlite'
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


def create_config():
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>'))
    print_formatted_text(HTML('<skyblue><b>Configuration file is not found</b></skyblue>'))
    print_formatted_text(HTML('<skyblue>You will be asked to enter settings</skyblue>'))
    print_formatted_text(HTML('<skyblue>and config file will be generated</skyblue>'))
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>\n'))

    # session = PromptSession()
    html_completer = WordCompleter(list(map(lambda x: x['name'], engines)))

    def promt_message(message):
        global promt_messages
        promt_messages += 1
        return HTML('{}. {}\n> '.format(promt_messages, message))

    address = prompt(
        promt_message('<green><b>Which host to run Jet Bridge on?</b></green>\n<i>Default is {}</i>'.format('0.0.0.0 (any IP)')),
        default='0.0.0.0'
    )

    print_formatted_text('')

    port = prompt(
        promt_message('<green><b>Which port?</b></green>\n<i>Default is {}</i>'.format('8888')),
        validator=Validator.from_callable(
            port_is_valid,
            error_message='Incorrect port',
            move_cursor_to_end=True
        ),
        default='8888'
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
        validate_while_typing=False
    )

    print_formatted_text('')

    if database_engine == 'sqlite':
        database_name = prompt(
            promt_message('<green><b>Enter your database file path</b></green>'),
            validator=Validator.from_callable(
                is_file_exists,
                error_message='File does not exist on given path',
                move_cursor_to_end=True
            )
        )

        database_host = ''
        database_port = ''
        database_user = ''
        database_password = ''
    else:
        database_host = prompt(
            promt_message('<green><b>Enter your database host</b></green>\n<i>Default is {}</i>'.format('localhost')),
            validator=Validator.from_callable(
                is_not_empty,
                error_message='Database host is required',
                move_cursor_to_end=True
            ),
            default='localhost'
        )

        print_formatted_text('')

        default_port = list(map(lambda x: str(x.get('default_port', '')), filter(
            lambda x: x['name'] == database_engine, engines
        )))[0]

        database_port = prompt(
            promt_message('<green><b>Enter your database port</b></green>'),
            validator=Validator.from_callable(
                is_not_empty,
                error_message='Database port is required',
                move_cursor_to_end=True
            ),
            default=default_port
        )

        print_formatted_text('')

        database_name = prompt(
            promt_message('<green><b>Enter your database name</b></green>'),
            validator=Validator.from_callable(
                is_not_empty,
                error_message='Database name is required',
                move_cursor_to_end=True
            )
        )

        print_formatted_text('')

        database_user = prompt(
            promt_message('<green><b>Enter your database user</b></green>'),
            validator=Validator.from_callable(
                is_not_empty,
                error_message='Database user is required',
                move_cursor_to_end=True
            )
        )

        print_formatted_text('')

        database_password = prompt(
            promt_message('<green><b>Enter your database password</b></green>')
        )

    print_formatted_text('')

    config = prompt(
        promt_message('<green><b>Where to store config file?</b></green>\nDefault is jet.conf inside current working directory\n[{}]'.format(os.path.abspath(settings.DEFAULT_CONFIG_PATH))),
        default=settings.DEFAULT_CONFIG_PATH
    )

    config_content = {
        'ADDRESS': address,
        'PORT': port,
        'CONFIG': config,
        'DATABASE_ENGINE': database_engine,
        'DATABASE_HOST': database_host,
        'DATABASE_PORT': database_port,
        'DATABASE_NAME': database_name,
        'DATABASE_USER': database_user,
        'DATABASE_PASSWORD': database_password
    }

    with open(config, 'w') as f:
        f.write('[JET]\n')
        for key, value in config_content.items():
            f.write('{}={}\n'.format(key, value))

    print_formatted_text('')
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>'))
    print_formatted_text(HTML('<skyblue><b>Configuration file is created at:</b></skyblue>'))
    print_formatted_text(HTML('<skyblue>{}</skyblue>'.format(os.path.abspath(config))))
    print_formatted_text('')
    print_formatted_text(HTML('<skyblue>You can now start <b>Jet Bridge</b> by running</skyblue>'))
    print_formatted_text(HTML('<skyblue><b>jet_bridge</b> command once again</skyblue>'))
    print_formatted_text(HTML('<skyblue><b>===========================================</b></skyblue>\n'))
