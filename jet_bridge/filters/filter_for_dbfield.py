import sqlalchemy

from jet_bridge.filters.char_filter import CharFilter


FILTER_FOR_DBFIELD = {
    # sqlalchemy.AutoField:                   {'filter_class': NumberFilter},
    sqlalchemy.VARCHAR: {'filter_class': CharFilter},
    # sqlalchemy.TextField:                   {'filter_class': CharFilter},
    # sqlalchemy.BOOLEAN:                {'filter_class': BooleanFilter},
    # sqlalchemy.DateField:                   {'filter_class': DateFilter},
    # sqlalchemy.DateTimeField:               {'filter_class': DateTimeFilter},
    # sqlalchemy.TimeField:                   {'filter_class': TimeFilter},
    # sqlalchemy.DurationField:               {'filter_class': DurationFilter},
    # sqlalchemy.DecimalField:                {'filter_class': NumberFilter},
    # sqlalchemy.SmallIntegerField:           {'filter_class': NumberFilter},
    # sqlalchemy.IntegerField:                {'filter_class': NumberFilter},
    # sqlalchemy.PositiveIntegerField:        {'filter_class': NumberFilter},
    # sqlalchemy.PositiveSmallIntegerField:   {'filter_class': NumberFilter},
    # sqlalchemy.FloatField:                  {'filter_class': NumberFilter},
    # sqlalchemy.NullBooleanField:            {'filter_class': BooleanFilter},
    # sqlalchemy.SlugField:                   {'filter_class': CharFilter},
    # sqlalchemy.EmailField:                  {'filter_class': CharFilter},
    # sqlalchemy.FilePathField:               {'filter_class': CharFilter},
    # sqlalchemy.URLField:                    {'filter_class': CharFilter},
    # sqlalchemy.GenericIPAddressField:       {'filter_class': CharFilter},
    # sqlalchemy.CommaSeparatedIntegerField:  {'filter_class': CharFilter},
    # sqlalchemy.UUIDField:                   {'filter_class': UUIDFilter}
}
FILTER_FOR_DBFIELD_DEFAULT = {'filter_class': CharFilter}
