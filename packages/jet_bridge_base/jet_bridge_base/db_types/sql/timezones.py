from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base.db_types import get_session_engine
from jet_bridge_base.utils.timezones import FixedOffsetTimezone


def sql_fetch_postgresql_default_timezone(session):
    try:
        cursor = session.execute('SELECT NOW()')
        row = cursor.fetchone()
        session.commit()

        return row[0].tzinfo
    except SQLAlchemyError:
        session.rollback()


def sql_fetch_mysql_default_timezone(session):
    try:
        cursor = session.execute('SELECT TIMEDIFF(NOW(), UTC_TIMESTAMP)')
        row = cursor.fetchone()
        session.commit()

        return FixedOffsetTimezone(row[0])
    except SQLAlchemyError:
        session.rollback()


def sql_fetch_mssql_default_timezone(session):
    try:
        cursor = session.execute('SELECT sysdatetimeoffset() as now')
        row = cursor.fetchone()
        session.commit()

        return row[0].tzinfo
    except SQLAlchemyError:
        session.rollback()


def sql_fetch_default_timezone(session):
    try:
        if get_session_engine(session) == 'postgresql':
            return sql_fetch_postgresql_default_timezone(session)
        elif get_session_engine(session) == 'mssql':
            return sql_fetch_mssql_default_timezone(session)
        elif get_session_engine(session) == 'mysql':
            return sql_fetch_mysql_default_timezone(session)
    except:
        pass
