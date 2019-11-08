import re

import six
from sqlalchemy import inspect

from jet_bridge_base.exceptions.validation_error import ValidationError


def serialize_validation_error(exc):
    def process(e, root=False):
        if isinstance(e.detail, dict):
            return dict(map(lambda x: (x[0], process(x[1])), e.detail.items()))
        elif isinstance(e.detail, list):
            return list(map(lambda x: process(x), e.detail))
        elif root:
            return {'non_field_errors': [e.detail]}
        else:
            return e.detail

    return process(exc, root=True)


def validation_error_from_database_error(e, model):
    if hasattr(e, 'orig'):
        if hasattr(e.orig, 'args') and hasattr(e.orig.args, '__getitem__'):
            if len(e.orig.args) == 1:
                message = e.orig.args[0]
            elif len(e.orig.args) == 2:
                message = e.orig.args[1]
            else:
                message = e.orig.args

            message = six.text_type(message)

            regex = [
                [r'Key\s\((.+)\)=\((.+)\)\salready\sexists', 1, 2],  # PostgreSQL
                [r'Duplicate\sentry\s\'(.+)\'\sfor key\s\'(.+)\'', 2, 1],  # MySQL
                [r'UNIQUE\sconstraint\sfailed\:\s(.+)\.(.+)', 2, None]  # SQLite
            ]

            for (r, field_index, value_index) in regex:
                match = re.search(r, message, re.IGNORECASE | re.MULTILINE)

                if match:
                    mapper = inspect(model)
                    columns = dict(map(lambda x: (x.key, x), mapper.columns))
                    column_name = match.group(field_index)

                    if column_name in columns:
                        error = dict()
                        error[column_name] = ValidationError('record with the same value already exists')
                        return ValidationError(error)

            return ValidationError(message)
    return ValidationError('Query failed')
