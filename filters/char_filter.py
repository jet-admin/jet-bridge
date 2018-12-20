from fields import CharField
from filters.filter import Filter


class CharFilter(Filter):
    field_class = CharField
