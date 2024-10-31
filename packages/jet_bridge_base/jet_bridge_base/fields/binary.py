from bson import ObjectId
import binascii

from jet_bridge_base.fields.field import Field


class BinaryField(Field):
    def to_internal_value_item(self, value):
        return binascii.unhexlify(value)

    def to_representation_item(self, value):
        if isinstance(value, bytes):
            return binascii.hexlify(value).decode('ascii')
        elif isinstance(value, ObjectId):
            return binascii.hexlify(value.binary).decode('ascii')
