import dateparser
from datetime import datetime

from .common import get_session_engine
from .mongo import MongoSession


def apply_session_timezone(session, timezone):
    if isinstance(session, MongoSession):
        pass
    else:
        if get_session_engine(session) == 'mysql':
            session.execute('SET time_zone = :tz', {'tz': timezone})
            session.info['_queries_timezone'] = timezone
        elif get_session_engine(session) in ['postgresql', 'mssql']:
            offset_hours = dateparser.parse(datetime.now().isoformat() + timezone).utcoffset().total_seconds() / 60 / 60
            offset_hours_str = '{:+}'.format(offset_hours).replace(".0", "")
            session.execute('SET TIME ZONE :tz', {'tz': offset_hours_str})
            session.info['_queries_timezone'] = timezone
