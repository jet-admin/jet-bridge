import os
import sys
import logging

from jet_bridge_base.logger import set_logger_level

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_MODULE = sys.modules[__name__]

DEBUG = False
READ_ONLY = False
AUTO_OPEN_REGISTER = True
PROJECT = None
TOKEN = None
ENVIRONMENT = None
CORS_HEADERS = True
BASE_URL = None
JWT_VERIFY_KEY = '-----BEGIN PUBLIC KEY-----\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyfJablscZmsh7eHisWHi\n/x2gJUjc9juL4VLkEpp6PH9Ah+wBtGmPF9nfoVlQsgH9hra63POiaLUzIwW/ewOl\njyPF0FJngsxreCxNs8lmd/WNXrcnazknFItkFFeXJuMTfoBPQGiZOmVYb14jmvkc\n9vMmeXYjrbT+95SVayN3E6DzLoHDhny4Mka1OsxvIP5s77s0dOo68TzoEfBVeuto\nI/dopG86DVu4wYVtYPITzJ4z47OFVPKCyYVyy5aR3+DUnmdK7xTRVr+iWmHpcr7e\nhoeVcL4CqAILZ0gd54kQmnHbg7Bu6x8JtQkiLU5TQvWzjiN00io4eydvIAkQTAaR\nmdd32O1vJbSHmLyCR2tEW/uV7P25naPUlkApxuLzh5C21S0XJxNJ/P07KSMymt5U\n1lWqt4CInpjAwMI8qs9MkEwJev5+yumxqIrDKcQLMR3TBLJZIb+rL1teCLOW28qB\nL6VSKhfKRIaXUdLpRwAcSuXraTzwa9oCCZa19tw3uizMeMFrCrv43YbyOsS9h7JQ\n8ixj/a1R/ud0fCrhXWUl7nKlz0b15koILLG1Ts+MUTmIaEnHTVEY74CfJVq7waw9\nx2kyzSzbsmMXvFkrVzTmyImTN631+gatU+npJ3vtcD9SooEZLOCLa4pb+DIsv9P1\nEeIEAh1VZC7s2qsQZsiYTG0CAwEAAQ==\n-----END PUBLIC KEY-----\n'
BEARER_AUTH_KEY = None
ENVIRONMENT_TYPE = None

WEB_BASE_URL = None
API_BASE_URL = None

DATABASE_ENGINE = None
DATABASE_HOST = None
DATABASE_PORT = None
DATABASE_USER = None
DATABASE_PASSWORD = None
DATABASE_NAME = None
DATABASE_EXTRA = None
DATABASE_CONNECTIONS = None
DATABASE_ONLY = None
DATABASE_EXCEPT = None
DATABASE_MAX_TABLES = None
DATABASE_SCHEMA = None

DATABASE_SSL_CA = None
DATABASE_SSL_CERT = None
DATABASE_SSL_KEY = None

DATABASE_SSH_HOST = None
DATABASE_SSH_PORT = None
DATABASE_SSH_USER = None
DATABASE_SSH_PRIVATE_KEY = None

COOKIE_SAMESITE = None
COOKIE_SECURE = None
COOKIE_DOMAIN = None
COOKIE_COMPRESS = None

STORE_PATH = None

SSO_APPLICATIONS = {}

ALLOW_ORIGIN = '*'

TRACK_DATABASES = ''
TRACK_DATABASES_ENDPOINT = ''
TRACK_DATABASES_AUTH = ''

TRACK_MODELS_ENDPOINT = ''
TRACK_MODELS_AUTH = ''

TRACK_QUERY_SLOW_TIME = None
TRACK_QUERY_HIGH_MEMORY = None

RELEASE_INACTIVE_GRAPHQL_SCHEMAS_TIMEOUT = None

DISABLE_AUTH = None


def set_settings(settings):
    for key, value in settings.items():
        if value is None:
            continue
        setattr(CURRENT_MODULE, key, value)

    level = logging.DEBUG if DEBUG else logging.INFO
    set_logger_level(level)
