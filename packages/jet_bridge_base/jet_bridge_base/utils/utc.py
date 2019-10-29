from datetime import tzinfo, timedelta


try:
    from datetime import timezone
    utc = timezone.utc
except ImportError:
    # Python 2
    class UTC(tzinfo):
        def utcoffset(self, dt):
            return timedelta(0)

        def tzname(self, dt):
            return "UTC"

        def dst(self, dt):
            return timedelta(0)

    utc = UTC()
