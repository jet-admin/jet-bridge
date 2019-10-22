from sqlalchemy.sql import sqltypes

from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.boolean_filter import BooleanFilter
from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.datetime_filter import DateTimeFilter
from jet_bridge_base.filters.wkt_filter import WKTFilter
from jet_bridge_base.filters.integer_filter import IntegerFilter

number_lookups = [
    lookups.EXACT,
    lookups.GT,
    lookups.GTE,
    lookups.LT,
    lookups.LTE,
    lookups.ICONTAINS,
    lookups.IN,
    lookups.IS_NULL,
]

datetime_lookups = [
    lookups.EXACT,
    lookups.GT,
    lookups.GTE,
    lookups.LT,
    lookups.LTE,
    lookups.ICONTAINS,
    lookups.IN,
    lookups.IS_NULL,
]

text_lookups = [
    lookups.EXACT,
    lookups.ICONTAINS,
    lookups.IN,
    lookups.STARTS_WITH,
    lookups.ENDS_WITH,
    lookups.IS_NULL,
]

boolean_lookups = [
    lookups.EXACT,
    lookups.IN,
    lookups.IS_NULL,
]

json_lookups = [
    lookups.JSON_ICONTAINS,
    lookups.IS_NULL,
]

geography_lookups = [
    lookups.COVEREDBY
]

FILTER_FOR_DBFIELD = {
    sqltypes.VARCHAR: {'filter_class': CharFilter, 'lookups': text_lookups},
    sqltypes.TEXT: {'filter_class': CharFilter, 'lookups': text_lookups},
    sqltypes.BOOLEAN: {'filter_class': BooleanFilter, 'lookups': boolean_lookups},
    sqltypes.INTEGER: {'filter_class': IntegerFilter, 'lookups': number_lookups},
    sqltypes.SMALLINT: {'filter_class': IntegerFilter, 'lookups': number_lookups},
    sqltypes.NUMERIC: {'filter_class': IntegerFilter, 'lookups': number_lookups},
    sqltypes.DATETIME: {'filter_class': DateTimeFilter, 'lookups': datetime_lookups},
    sqltypes.TIMESTAMP: {'filter_class': DateTimeFilter, 'lookups': datetime_lookups},
    sqltypes.JSON: {'filter_class': CharFilter, 'lookups': json_lookups},
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
FILTER_FOR_DBFIELD_DEFAULT = FILTER_FOR_DBFIELD[sqltypes.VARCHAR]

try:
    from geoalchemy2 import types
    FILTER_FOR_DBFIELD[types.Geometry] = {'filter_class': WKTFilter, 'lookups': geography_lookups}
    FILTER_FOR_DBFIELD[types.Geography] = {'filter_class': WKTFilter, 'lookups': geography_lookups}
except ImportError:
    pass


def filter_for_data_type(value):
    for date_type, filter_data in FILTER_FOR_DBFIELD.items():
        if isinstance(value, date_type):
            return filter_data
    return FILTER_FOR_DBFIELD_DEFAULT
