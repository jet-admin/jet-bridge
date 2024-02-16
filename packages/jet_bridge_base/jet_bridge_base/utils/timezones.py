from datetime import tzinfo, timedelta

from jet_bridge_base.utils.queryset import get_session_engine


class FixedOffsetTimezone(tzinfo):
    def __init__(self, offset):
        self.offset = offset
        self.name = self.__class__.__name__

    def tzname(self, dt):
        return str(self.offset)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        return timedelta(0)

    def __repr__(self):
        total_hours = round(timedelta().total_seconds() / 60)
        return 'FixedOffsetTimezone(offset={})'.format(total_hours)


def fetch_postgresql_default_timezone(session):
    cursor = session.execute('SELECT NOW()')
    row = cursor.fetchone()

    return row[0].tzinfo


def fetch_mysql_default_timezone(session):
    cursor = session.execute('SELECT TIMEDIFF(NOW(), UTC_TIMESTAMP)')
    row = cursor.fetchone()

    return FixedOffsetTimezone(row[0])


def fetch_mssql_default_timezone(session):
    cursor = session.execute('SELECT sysdatetimeoffset() as now')
    row = cursor.fetchone()

    return row[0].tzinfo


def fetch_default_timezone(session):
    try:
        if get_session_engine(session) == 'postgresql':
            return fetch_postgresql_default_timezone(session)
        elif get_session_engine(session) == 'mssql':
            return fetch_mssql_default_timezone(session)
        elif get_session_engine(session) == 'mysql':
            return fetch_mysql_default_timezone(session)
    except:
        pass
