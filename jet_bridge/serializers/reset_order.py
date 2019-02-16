from sqlalchemy import desc, case
from sqlalchemy.orm import load_only

from jet_bridge import fields
from jet_bridge.serializers.serializer import Serializer


def get_reset_order_serializer(Model, queryset, session):
    class ResetOrderSerializer(Serializer):
        ordering_field = fields.CharField()
        ordering = fields.CharField(required=False, allow_null=True)
        value_ordering = fields.CharField(required=False, allow_null=True)

        def save(self):
            ordering_field = self.validated_data['ordering_field']
            ordering = self.validated_data.get('ordering')
            value_ordering = self.validated_data.get('value_ordering')

            qs = queryset
            order_by = []

            if value_ordering:
                field, values_str = value_ordering.split('-', 2)
                values = values_str.split(',')
                order_by.append(case(
                    [(getattr(Model, field) == x, i) for i, x in enumerate(values)],
                    else_=len(values)
                ))

            if ordering:
                def map_field(name):
                    descending = False
                    if name.startswith('-'):
                        name = name[1:]
                        descending = True
                    field = getattr(Model, name)
                    if descending:
                        field = desc(field)
                    return field

                order_by.extend(map(lambda x: map_field(x), ordering.split(',')))

            if len(order_by):
                qs = qs.order_by(*order_by)

            i = 1

            for instance in qs.options(load_only(ordering_field)):
                setattr(instance, ordering_field, i)
                i += 1

            session.commit()

    return ResetOrderSerializer
