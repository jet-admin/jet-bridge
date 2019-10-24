from jet_bridge_base.fields.field import Field


class WKTField(Field):

    def to_internal_value_item(self, value):
        if value is None:
            return
        from geoalchemy2 import WKTElement
        return WKTElement(value)

    def to_representation_item(self, value):
        if value is None:
            return
        from geoalchemy2.shape import to_shape
        return to_shape(value).to_wkt()
