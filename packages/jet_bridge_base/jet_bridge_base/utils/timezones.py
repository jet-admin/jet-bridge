from datetime import tzinfo, timedelta

from jet_bridge_base.utils.queryset import get_session_engine


class FixedOffsetTimezone(tzinfo):
    def __init__(self, offset):
        self.offset = offset
        self.name = 'Etc/GMT%+d' % (offset.total_seconds() / 60 / 60)

    def tzname(self, dt):
        return self.name

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        return timedelta(0)

    def __repr__(self):
        return 'FixedOffsetTimezone(name={}, offset={})'.format(self.name, self.offset)


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
