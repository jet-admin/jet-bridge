import json
import os

from tornado.options import define, options

from jet_bridge_base.logger import logger

from jet_bridge import media
from jet_bridge.utils.settings import parse_environment, parse_config_file

# Constants

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join('jet.conf')

# Options

DEFAULT_WEB_BASE_URL = 'https://app.jetadmin.io'
DEFAULT_API_BASE_URL = 'https://api.jetadmin.io/api'

define('address', default='0.0.0.0', help='server address')
define('port', default=8888, help='server port', type=int)
define('workers', default=1, help='number of workers', type=int)
define('config', default=DEFAULT_CONFIG_PATH, help='config file path')
define('use_default_config', default='', help='use default config values')
define('debug', default=False, help='debug mode', type=bool)
define('read_only', default=False, help='read only', type=bool)
define('threads', default=None, help='threads', type=int)
define('connections', default=50, help='connects', type=int)
define('auto_open_register', default=True, help='open token register automatically', type=bool)
define('project', help='project', type=str)
define('token', help='token', type=str)
define('environment', help='environment', type=str)
define('cors_headers', default=True, help='add CORS headers', type=bool)
define('base_url', help='base URL', type=str)
define('jwt_verify_key', help='JWT verify key', type=str, default=None)
define('bearer_auth_key', help='Bearer auth key', type=str, default=None)
define('environment_type', help='environment type', type=str, default=None)

define('web_base_url', default=DEFAULT_WEB_BASE_URL, help='Jet Admin frontend application base URL')
define('api_base_url', default=DEFAULT_API_BASE_URL, help='Jet Admin API base URL')

define('media_storage', default=media.MEDIA_STORAGE_FILE, help='media storage type')
define('media_root', default='media', help='media root')
define('media_base_url', default=None, help='media base URL')

define('database_engine', help='database engine (postgresql, mysql, oracle, mssql+pyodbc, bigquery, snowflake, sqlite)')
define('database_host', help='database host')
define('database_port', help='database port')
define('database_user', help='database user')
define('database_password', help='database password')
define('database_name', help='database name or path')
define('database_extra', default=None, help='database extra parameters')
define('database_only', default=None, type=str)
define('database_except', default=None, type=str)
define('database_schema', default=None, type=str)

define('database_ssh_host', default=None, type=str)
define('database_ssh_port', default=None, type=int)
define('database_ssh_user', default=None, type=str)
define('database_ssh_private_key', default=None, type=str)

define('cookie_samesite', default='None', type=str)
define('cookie_secure', default=True, type=bool)
define('cookie_domain', default=None, type=str)
define('cookie_compress', default=False, type=bool)

define('store_path', default='jet_bridge_store.sqlite3', type=str)

define('sso_applications', default='{}', type=str)
define('allow_origin', default='*')

define('track_databases', default='')
define('track_databases_endpoint', default='')
define('track_databases_auth', default='')

define('track_models_endpoint', default='')
define('track_models_auth', default='')

# Parse

options.parse_command_line(final=False)

if options.config:
    try:
        parse_config_file(options, options.config, 'JET', final=False)
    except IOError as e:
        if options.config != DEFAULT_CONFIG_PATH:
            logger.warning(e)

parse_environment(options, final=True)

required_options = [
    'address',
    'port',
    'project',
    'token',
    'database_engine'
]

required_options_without_default = [
    # 'project',
    # 'token',
    'database_engine'
]

if options.database_engine != 'none':
    required_options.append('database_name')
    required_options_without_default.append('database_name')

missing_options = list(filter(lambda x: x not in options or options[x] is None, required_options))

# Settings

ADDRESS = options.address
PORT = options.port
WORKERS = options.workers
DEBUG = options.debug
READ_ONLY = options.read_only
THREADS = options.threads
CONNECTIONS = options.connections
AUTO_OPEN_REGISTER = options.auto_open_register
CONFIG = options.config
USE_DEFAULT_CONFIG = options.use_default_config.lower().split(',')
PROJECT = options.project
TOKEN = options.token
ENVIRONMENT = options.environment
CORS_HEADERS = options.cors_headers
BASE_URL = options.base_url
JWT_VERIFY_KEY = options.jwt_verify_key
BEARER_AUTH_KEY = options.bearer_auth_key
ENVIRONMENT_TYPE = options.environment_type

WEB_BASE_URL = options.web_base_url
API_BASE_URL = options.api_base_url

MEDIA_STORAGE = options.media_storage
MEDIA_ROOT = options.media_root
MEDIA_BASE_URL = options.media_base_url

DATABASE_ENGINE = options.database_engine
DATABASE_HOST = options.database_host
DATABASE_PORT = options.database_port
DATABASE_USER = options.database_user
DATABASE_PASSWORD = options.database_password
DATABASE_NAME = options.database_name
DATABASE_EXTRA = options.database_extra
DATABASE_ONLY = options.database_only.split(',') if options.database_only else None
DATABASE_EXCEPT = options.database_except.split(',') if options.database_except else None
DATABASE_SCHEMA = options.database_schema

DATABASE_SSH_HOST = options.database_ssh_host
DATABASE_SSH_PORT = options.database_ssh_port
DATABASE_SSH_USER = options.database_ssh_user
DATABASE_SSH_PRIVATE_KEY = options.database_ssh_private_key

COOKIE_SAMESITE = options.cookie_samesite
COOKIE_SECURE = options.cookie_secure
COOKIE_DOMAIN = options.cookie_domain
COOKIE_COMPRESS = options.cookie_compress

STORE_PATH = options.store_path

try:
    SSO_APPLICATIONS = json.loads(options.sso_applications)
except Exception as e:
    logger.error('SSO_APPLICATIONS parsing failed', exc_info=e)
    SSO_APPLICATIONS = {}

ALLOW_ORIGIN = options.allow_origin

TRACK_DATABASES = options.track_databases
TRACK_DATABASES_ENDPOINT = options.track_databases_endpoint
TRACK_DATABASES_AUTH = options.track_databases_auth

TRACK_MODELS_ENDPOINT = options.track_models_endpoint
TRACK_MODELS_AUTH = options.track_models_auth

POSSIBLE_HOST = os.environ.get('POSSIBLE_HOST')
