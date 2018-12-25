import os
from tornado.options import Error


def parse_environment(self, final=True):
    for name in os.environ:
        normalized = self._normalize_name(name)
        normalized = normalized.lower()
        if normalized in self._options:
            option = self._options[normalized]
            if option.multiple:
                if not isinstance(os.environ[name], (list, str)):
                    raise Error("Option %r is required to be a list of %s "
                                "or a comma-separated string" %
                                (option.name, option.type.__name__))

            if type(os.environ[name]) == str and option.type != str:
                option.parse(os.environ[name])
            else:
                option.set(os.environ[name])
