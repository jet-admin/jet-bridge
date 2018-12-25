from jet_bridge import fields


class SqlParamsSerializers(fields.CharField):

    def to_internal_value_item(self, value):
        value = super().to_internal_value(value)
        if value == '':
            return []
        # value = list(filter(lambda x: x != '', value.split(',')))
        value = value.split(',')
        return dict([['param_{}'.format(i), x] for i, x in enumerate(value)])

    def to_representation_item(self, value):
        return list(value)
