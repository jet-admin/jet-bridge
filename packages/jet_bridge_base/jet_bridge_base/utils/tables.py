def get_table_name(metadata, table):
    if table.schema and table.schema != metadata.schema:
        return '{}.{}'.format(table.schema, table.name)
    else:
        return str(table.name)
