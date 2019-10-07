from sqlalchemy import inspect

from jet_bridge_base import fields
from jet_bridge_base.serializers.serializer import Serializer


def get_reorder_serializer(Model, queryset, session):
    class ReorderSerializer(Serializer):
        ordering_field = fields.CharField()
        forward = fields.BooleanField()
        segment_from = fields.IntegerField()
        segment_to = fields.IntegerField()
        item = fields.IntegerField()
        segment_by_ordering_field = fields.BooleanField(default=False)

        def save(self):
            mapper = inspect(Model)

            primary_key_field = mapper.primary_key[0].name
            ordering_field = self.validated_data['ordering_field']
            primary_key = getattr(Model, primary_key_field)
            ordering = getattr(Model, ordering_field)

            if self.validated_data.get('segment_by_ordering_field'):
                segment_from = self.validated_data['segment_from']
                segment_to = self.validated_data['segment_to']
            else:
                segment_from_instance = queryset.filter(primary_key == self.validated_data['segment_from']).first()
                segment_to_instance = queryset.filter(primary_key == self.validated_data['segment_to']).first()

                segment_from = getattr(segment_from_instance, ordering_field)
                segment_to = getattr(segment_to_instance, ordering_field)

            if self.validated_data['forward']:
                queryset.filter(
                    ordering >= segment_from,
                    ordering <= segment_to
                ).update(
                    {ordering_field: ordering - 1}
                )
                queryset.filter(
                    primary_key == self.validated_data['item']
                ).update(
                    {ordering_field: segment_to}
                )
            else:
                queryset.filter(
                    ordering >= segment_from,
                    ordering <= segment_to
                ).update(
                    {ordering_field: ordering + 1}
                )
                queryset.filter(
                    primary_key == self.validated_data['item']
                ).update(
                    {ordering_field: segment_to}
                )

            session.commit()

    return ReorderSerializer
