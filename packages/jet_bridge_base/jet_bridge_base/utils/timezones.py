from datetime import tzinfo, timedelta


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
