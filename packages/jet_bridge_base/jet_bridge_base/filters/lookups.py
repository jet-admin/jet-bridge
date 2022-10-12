
EXACT = 'exact'
GT = 'gt'
GTE = 'gte'
LT = 'lt'
LTE = 'lte'
ICONTAINS = 'icontains'
IN = 'in'
STARTS_WITH = 'istartswith'
ENDS_WITH = 'iendswith'
IS_NULL = 'isnull'
JSON_ICONTAINS = 'json_icontains'
COVEREDBY = 'coveredby'
DEFAULT_LOOKUP = EXACT


def by_gql(name):
    if name == 'eq':
        return EXACT
    elif name == 'gt':
        return GT
    elif name == 'gte':
        return GTE
    elif name == 'lt':
        return LT
    elif name == 'lte':
        return LTE
    elif name == 'containsI':
        return ICONTAINS
    elif name == 'in':
        return IN
    elif name == 'startsWithI':
        return STARTS_WITH
    elif name == 'endsWithI':
        return ENDS_WITH
    elif name == 'isNull':
        return IS_NULL
    elif name == 'jsonContainsI':
        return JSON_ICONTAINS
    elif name == 'coveredBy':
        return COVEREDBY
