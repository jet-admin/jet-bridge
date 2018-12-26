from __future__ import absolute_import, unicode_literals

import datetime
import decimal
import json  # noqa
import uuid
import six


class JSONEncoder(json.JSONEncoder):

    def is_aware(self, value):
        return value.utcoffset() is not None

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            if representation.endswith('+00:00'):
                representation = representation[:-6] + 'Z'
            return representation
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            if self.is_aware(obj):
                raise ValueError("JSON can't represent timezone-aware times.")
            representation = obj.isoformat()
            return representation
        elif isinstance(obj, datetime.timedelta):
            return six.text_type(obj.total_seconds())
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return six.text_type(obj)
        elif isinstance(obj, six.binary_type):
            return obj.decode('utf-8')
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, '__getitem__'):
            try:
                return dict(obj)
            except Exception:
                pass
        elif hasattr(obj, '__iter__'):
            return tuple(item for item in obj)
        return super(JSONEncoder, self).default(obj)
