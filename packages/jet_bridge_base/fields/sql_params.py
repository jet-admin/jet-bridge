from jet_bridge_base import fields


class SqlParamsSerializers(fields.CharField):

    def to_internal_value_item(self, value):
        value = super(SqlParamsSerializers, self).to_internal_value_item(value)
        if value is None:
            return []
        # value = list(filter(lambda x: x != '', value.split(',')))
        value = value.split(',')
        return dict([['param_{}'.format(i), x] for i, x in enumerate(value)])

    def to_representation_item(self, value):
        return list(value)
