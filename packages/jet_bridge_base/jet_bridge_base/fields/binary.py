from jet_bridge_base.fields.field import Field
import binascii


class BinaryField(Field):
    def to_internal_value_item(self, value):
        return binascii.unhexlify(value)

    def to_representation_item(self, value):
        if isinstance(value, bytes):
            return binascii.hexlify(value).decode('ascii')
