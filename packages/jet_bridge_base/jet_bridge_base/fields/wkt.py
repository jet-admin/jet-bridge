import six

from jet_bridge_base.fields.field import Field


class WKTField(Field):
    field_error_messages = {
        'invalid': 'not a valid Geo object - {error}'
    }

    def to_internal_value_item(self, value):
        if value is None:
            return
        from geoalchemy2 import ArgumentError, WKTElement
        try:
            return WKTElement(value)
        except ArgumentError as e:
            self.error('invalid', error=six.text_type(e))

    def to_representation_item(self, value):
        if value is None:
            return
        from geoalchemy2.shape import to_shape
        shape = to_shape(value)
        if hasattr(shape, 'wkt'):
            return shape.wkt
        else:
            # Backward compatibility Shapely <1.8.0
            return shape.to_wkt()
